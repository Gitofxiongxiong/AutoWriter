import cv2
import numpy as np


#像素坐标系是左手坐标系
#grbl是右手坐标系。坐标转换出来的应该要是右手坐标系，此处应该将坐标系对齐！！
class CoordinateConverter:
    def __init__(self, aruco_dict_type = cv2.aruco.DICT_4X4_50,
                 ref_marker1_id = 1, ref_marker2_id = 2, pen_marker_id = 3,
                 marker_size_mm = 20,
                 ref_marker1_world_center_mm = (0,0), ref_marker2_world_center_mm = (0,50)):
        """
        初始化坐标转换器
        
        使用右手坐标系，x轴正方向向右，y轴正方向向上

        参数:
        aruco_dict_type (cv2.aruco.Dictionary_Type): ArUco字典类型, 例如 cv2.aruco.DICT_4X4_100
        ref_marker1_id (int): 参考标签1的ID (例如，原点标签)
        ref_marker2_id (int): 参考标签2的ID (例如，X轴上的点)
        pen_marker_id (int): 笔夹上的标签ID
        marker_size_mm (float): ArUco标签的边长 (毫米)
        ref_marker1_world_center_mm (tuple): 参考标签1中心点的世界坐标 (x, y) in mm
        ref_marker2_world_center_mm (tuple): 参考标签2中心点的世界坐标 (x, y) in mm
        """
        try:
            # For OpenCV 4.7.0 and later
            self.aruco_dict = cv2.aruco.getPredefinedDictionary(aruco_dict_type)
            self.aruco_params = cv2.aruco.DetectorParameters()
            self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        except AttributeError:
            # For older OpenCV versions (e.g., 3.x, early 4.x)
            self.aruco_dict = cv2.aruco.Dictionary_get(aruco_dict_type)
            self.aruco_params = cv2.aruco.DetectorParameters_create()
            # Note: In very old versions, detection might be a direct cv2.aruco.detectMarkers call
            # without a separate detector object. The detect_markers method handles this.


        self.ref_marker1_id = ref_marker1_id
        self.ref_marker2_id = ref_marker2_id
        self.pen_marker_id = pen_marker_id
        self.marker_size_mm = marker_size_mm
        self.half_marker_size_mm = marker_size_mm / 2.0

        # 定义参考标签在世界坐标系中的角点坐标 (顺序: 左上, 右上, 右下, 左下) 
        # 这是计算单应性矩阵的关键
        # 修改为右手坐标系：y轴正方向向上，所以y坐标取反
        self.world_points_ref_marker1 = np.array([
            [ref_marker1_world_center_mm[0] - self.half_marker_size_mm, -(ref_marker1_world_center_mm[1] - self.half_marker_size_mm)],
            [ref_marker1_world_center_mm[0] + self.half_marker_size_mm, -(ref_marker1_world_center_mm[1] - self.half_marker_size_mm)],
            [ref_marker1_world_center_mm[0] + self.half_marker_size_mm, -(ref_marker1_world_center_mm[1] + self.half_marker_size_mm)],
            [ref_marker1_world_center_mm[0] - self.half_marker_size_mm, -(ref_marker1_world_center_mm[1] + self.half_marker_size_mm)]
        ], dtype=np.float32)

        self.world_points_ref_marker2 = np.array([
            [ref_marker2_world_center_mm[0] - self.half_marker_size_mm, -(ref_marker2_world_center_mm[1] - self.half_marker_size_mm)],
            [ref_marker2_world_center_mm[0] + self.half_marker_size_mm, -(ref_marker2_world_center_mm[1] - self.half_marker_size_mm)],
            [ref_marker2_world_center_mm[0] + self.half_marker_size_mm, -(ref_marker2_world_center_mm[1] + self.half_marker_size_mm)],
            [ref_marker2_world_center_mm[0] - self.half_marker_size_mm, -(ref_marker2_world_center_mm[1] + self.half_marker_size_mm)]
        ], dtype=np.float32)

        self.homography_matrix = None
        self.inv_homography_matrix = None
        self.reference_markers_found_last_update = False

    def detect_markers(self, image):
        """
        在图像中检测ArUco标签。

        参数:
        image (numpy.ndarray): 输入图像 (建议灰度图以提高速度和稳定性)

        返回:
        tuple: (detected_markers_info, raw_corners, raw_ids)
                 detected_markers_info (dict): 键为标签ID，值为包含其角点和中心像素坐标的字典。
                 raw_corners: cv2.aruco.detectMarkers的原始角点输出
                 raw_ids: cv2.aruco.detectMarkers的原始ID输出
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 and image.shape[2] == 3 else image

        try:
            # Using ArucoDetector object (OpenCV 4.7.0+)
            corners, ids, rejected = self.detector.detectMarkers(gray)
        except AttributeError:
            # Using global detectMarkers function (older OpenCV)
            corners, ids, rejected = cv2.aruco.detectMarkers(gray, self.aruco_dict, parameters=self.aruco_params)

        detected_markers_info = {}
        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                marker_corners_px = corners[i].reshape((4, 2)) # (4, 2) array of pixel coordinates
                center_px = np.mean(marker_corners_px, axis=0) # (x, y) pixel center
                detected_markers_info[marker_id] = {
                    "corners_px": marker_corners_px,
                    "center_px": center_px
                }
        return detected_markers_info, corners, ids

    def update_homography(self, image):
        """
        检测参考标签并计算/更新单应性矩阵。

        参数:
        image (numpy.ndarray): 当前摄像头帧

        返回:
        bool: 如果成功计算了单应性矩阵则返回True，否则False。
        """
        detected_markers_info, _, _ = self.detect_markers(image)

        ref1_info = detected_markers_info.get(self.ref_marker1_id)
        ref2_info = detected_markers_info.get(self.ref_marker2_id)

        if ref1_info and ref2_info:
            world_pts = np.vstack((self.world_points_ref_marker1, self.world_points_ref_marker2))
            pixel_pts = np.vstack((ref1_info["corners_px"], ref2_info["corners_px"]))
            print("world_pts:", world_pts)
            print("pixel_pts:", pixel_pts)

            self.homography_matrix, mask = cv2.findHomography(world_pts, pixel_pts, cv2.RANSAC, 5.0)

            if self.homography_matrix is not None:
                try:
                    self.inv_homography_matrix = np.linalg.inv(self.homography_matrix)
                    self.reference_markers_found_last_update = True
                    return True
                except np.linalg.LinAlgError:
                    print("错误: 单应性矩阵不可逆。")
                    self.homography_matrix = None
                    self.inv_homography_matrix = None
                    self.reference_markers_found_last_update = False
                    return False
            else:
                print("错误: 未能计算单应性矩阵。确保参考标签清晰可见且配置正确。")
                self.reference_markers_found_last_update = False
                return False
        else:
            # print("错误: 未能同时检测到两个参考ArUco标签。") # 可以取消注释以进行更详细的调试
            self.reference_markers_found_last_update = False
            return False

    def world_to_pixel(self, world_coords_mm):
        """
        将世界坐标 (mm) 转换为像素坐标。

        参数:
        world_coords_mm (tuple or np.array): 世界坐标 (x, y) in mm.

        返回:
        tuple or None: 像素坐标 (px, py) 如果转换成功，否则None。
        """
        if self.homography_matrix is None:
            print("错误: 单应性矩阵未初始化。请先调用 update_homography。")
            return None

        world_pt_homogeneous = np.array([world_coords_mm[0], world_coords_mm[1], 1.0], dtype=np.float32)
        pixel_pt_homogeneous = self.homography_matrix @ world_pt_homogeneous
        
        if pixel_pt_homogeneous[2] == 0: # 避免除以零
            return None
        
        # 转换为非齐次坐标
        pixel_x = pixel_pt_homogeneous[0] / pixel_pt_homogeneous[2]
        pixel_y = pixel_pt_homogeneous[1] / pixel_pt_homogeneous[2]
        
        return (pixel_x, pixel_y)


    def pixel_to_world(self, pixel_coords):
        """
        将像素坐标转换为世界坐标 (mm)。

        参数:
        pixel_coords (tuple or np.array): 像素坐标 (px, py).

        返回:
        tuple or None: 世界坐标 (x, y) in mm 如果转换成功，否则None。
        """
        if self.inv_homography_matrix is None:
            print("错误: 逆单应性矩阵未初始化。请先调用 update_homography。")
            return None

        pixel_pt_homogeneous = np.array([pixel_coords[0], pixel_coords[1], 1.0], dtype=np.float32)
        world_pt_homogeneous = self.inv_homography_matrix @ pixel_pt_homogeneous

        if world_pt_homogeneous[2] == 0: # 避免除以零
            return None
            
        # 转换为非齐次坐标
        world_x = world_pt_homogeneous[0] / world_pt_homogeneous[2]
        world_y = world_pt_homogeneous[1] / world_pt_homogeneous[2]

        return (world_x, world_y)

    def get_pen_marker_world_position(self, image):
        """
        获取笔夹上ArUco标签中心点的世界坐标。

        参数:
        image (numpy.ndarray): 当前摄像头帧

        返回:
        tuple or None: 笔标签的世界坐标 (x, y) in mm，如果未找到或转换失败则返回None。
        """
        if not self.reference_markers_found_last_update:
            # print("警告: 参考单应性矩阵可能不是最新的或无效。尝试更新...")
            if not self.update_homography(image):
                 print("错误: 单应性矩阵未初始化且更新失败。无法获取笔位置。")
                 return None

        detected_markers_info, _, _ = self.detect_markers(image)
        pen_marker_info = detected_markers_info.get(self.pen_marker_id)

        if pen_marker_info:
            pen_center_px = pen_marker_info["center_px"]
            return self.pixel_to_world(pen_center_px)
        else:
            # print(f"警告: 未在图像中找到笔标签 (ID: {self.pen_marker_id})。")
            return None

    def draw_detected_markers_on_image(self, image, detected_corners, detected_ids, color=(0, 255, 0)):
        """
        在图像上绘制检测到的标签的边界和ID
        
        参数:
        image: 要绘制的图像
        detected_corners: 检测到的角点
        detected_ids: 检测到的ID
        color: BGR颜色元组，默认为绿色(0, 255, 0)
        """
        if detected_ids is not None and len(detected_ids) > 0:
            # 手动绘制边框和ID
            for i in range(len(detected_ids)):
                corners = detected_corners[i].reshape((4, 2))
                corners = corners.astype(int)
                
                # 绘制边框
                for j in range(4):
                    pt1 = (corners[j][0], corners[j][1])
                    pt2 = (corners[(j + 1) % 4][0], corners[(j + 1) % 4][1])
                    cv2.line(image, pt1, pt2, color, 2)
                
                # 绘制ID
                center_x = int(np.mean(corners[:, 0]))
                center_y = int(np.mean(corners[:, 1]))
                cv2.putText(image, str(detected_ids[i][0]), 
                           (center_x, center_y),
                           cv2.FONT_HERSHEY_SIMPLEX,
                           2, color, 10)
        return image

# --- 示例用法 ---
if __name__ == "__main__":
    # 配置参数
    REF_MARKER1_ID = 1
    REF_MARKER2_ID = 2
    PEN_MARKER_ID = 3  # 假设笔夹上的标签ID为3
    MARKER_SIZE_MM = 20.0
    REF_MARKER1_WORLD_CENTER_MM = (0.0, 0.0)
    REF_MARKER2_WORLD_CENTER_MM = (0, -50)

    # 选择一个ArUco字典 (确保与您打印的标签一致)
    # 例如: cv2.aruco.DICT_4X4_50, cv2.aruco.DICT_6X6_250, etc.
    ARUCO_DICT_TYPE = cv2.aruco.DICT_4X4_100

    converter = CoordinateConverter(
        aruco_dict_type=ARUCO_DICT_TYPE,
        ref_marker1_id=REF_MARKER1_ID,
        ref_marker2_id=REF_MARKER2_ID,
        pen_marker_id=PEN_MARKER_ID,
        marker_size_mm=MARKER_SIZE_MM,
        ref_marker1_world_center_mm=REF_MARKER1_WORLD_CENTER_MM,
        ref_marker2_world_center_mm=REF_MARKER2_WORLD_CENTER_MM
    )

    # 模拟从摄像头捕获帧 (在实际应用中，您会使用cv2.VideoCapture)
    # cap = cv2.VideoCapture(0) # 或者视频文件路径

    # 为了演示，我们加载一个示例图片。您需要替换为您的摄像头帧。
    # 请确保图片 'aruco_test_image.png' 存在于脚本同目录下，
    # 或者提供正确的路径。该图片应包含ID为1, 2, 3的ArUco标签。
    try:
        # 创建一个简单的测试图像，如果实际图像不可用
        # 您应该替换为真实的摄像头帧或图像文件
        # frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # cv2.putText(frame, "No camera feed. Replace with actual image.", (50, 240),
        #             cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        # 尝试加载一个实际的测试图片（如果存在）
        frame = cv2.imread(r"F:\typewriter\test_pic\IMG_20250509_180759.jpg")
        if frame is None:
            raise FileNotFoundError("Test image not found.")
        print("提示: 当前使用的是占位符图像。请替换为您的摄像头帧或实际图像文件进行测试。")

    except FileNotFoundError as e:
        print(e)
        print("请确保 'your_image_with_aruco_markers.png' 存在或修改代码以从摄像头读取。")
        exit()


    # --- 主循环 (模拟摄像头处理) ---
    # while True: # 在实际应用中
        # ret, frame = cap.read()
        # if not ret:
        #     print("无法获取摄像头帧")
        #     break

    # 1. 更新单应性矩阵 (如果相机或工作平面固定，可以在开始时或定期执行)
    #    对于桌面应用，如果设置好后不动，启动时更新一次可能就够了。
    #    如果需要鲁棒性，可以每帧或每隔几帧更新。
    success_homography = converter.update_homography(frame)
    if success_homography:
        print("单应性矩阵已成功初始化/更新。")
    else:
        print("警告: 未能初始化/更新单应性矩阵。坐标转换将不可用。")
        # 在实际应用中，这里可能需要等待或提示用户检查标签

    # 创建一个副本用于绘制调试信息
    debug_image = frame.copy()

    # 2. 检测所有可见标签 (主要用于调试或获取笔标签信息)
    #    update_homography 内部已经调用了 detect_markers,
    #    如果只是为了获取笔位置，可以直接调用 get_pen_marker_world_position
    #    这里再次调用是为了获取原始角点和ID用于绘制
    detected_markers_info, raw_corners, raw_ids = converter.detect_markers(frame)

    # 在图像上绘制检测到的标签的边界和ID
    debug_image = converter.draw_detected_markers_on_image(debug_image, raw_corners, raw_ids)

    # 在参考标签和笔标签上画出其检测到的像素中心点
    for marker_id, info in detected_markers_info.items():
        center_px = tuple(map(int, info['center_px']))
        cv2.circle(debug_image, center_px, 4, (0,0,255), -1) # 红色圆点标记中心
        cv2.putText(debug_image, f"ID:{marker_id}", (center_px[0]+10, center_px[1]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), 2)


    if success_homography: # 仅当单应性矩阵有效时才进行转换
        # 3. 获取笔的世界坐标
        pen_world_pos_mm = converter.get_pen_marker_world_position(frame)
        if pen_world_pos_mm:
            print(f"笔的估计世界坐标 (mm): ({pen_world_pos_mm[0]:.2f}, {pen_world_pos_mm[1]:.2f})")
            # 为了显示，将笔的世界坐标转换回像素坐标，并在图上标记
            pen_display_px = converter.world_to_pixel(pen_world_pos_mm)
            if pen_display_px:
                cv2.putText(debug_image, f"Pen World: ({pen_world_pos_mm[0]:.1f}, {pen_world_pos_mm[1]:.1f})mm",
                            (int(pen_display_px[0]) - 50, int(pen_display_px[1]) - 20), # 调整文本位置
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 1, cv2.LINE_AA)
                cv2.circle(debug_image, (int(pen_display_px[0]), int(pen_display_px[1])), 5, (0, 255, 255), -1) # 黄色标记笔的转换后位置

        # 4. 示例：将一个已知的世界坐标点转换为像素坐标
        target_world_mm = (25.0, 10.0) # 假设这是写字机要去的目标点 (25mm, 10mm)
        target_pixel = converter.world_to_pixel(target_world_mm)
        if target_pixel:
            print(f"世界坐标 {target_world_mm} mm 对应的像素坐标: ({target_pixel[0]:.2f}, {target_pixel[1]:.2f})")
            cv2.circle(debug_image, (int(target_pixel[0]), int(target_pixel[1])), 6, (0,255,0), -1) # 绿色圆点标记目标
            cv2.putText(debug_image, "Target (W->P)", (int(target_pixel[0])+10, int(target_pixel[1])),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1, cv2.LINE_AA)

        # 5. 示例：将一个已知的像素坐标点 (例如图像中心附近的一个点) 转换为世界坐标
        sample_pixel_coord = (debug_image.shape[1] // 2, debug_image.shape[0] // 2) # 图像中心
        sample_world_mm = converter.pixel_to_world(sample_pixel_coord)
        if sample_world_mm:
            print(f"像素坐标 {sample_pixel_coord} 对应的世界坐标 (mm): ({sample_world_mm[0]:.2f}, {sample_world_mm[1]:.2f})")
            cv2.circle(debug_image, sample_pixel_coord, 6, (255,0,255), -1) # 紫色圆点标记
            cv2.putText(debug_image, f"Sample (P->W): ({sample_world_mm[0]:.1f}, {sample_world_mm[1]:.1f})mm",
                        (sample_pixel_coord[0]+10, sample_pixel_coord[1]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,255), 1, cv2.LINE_AA)

        white_points = [(1025,290), (1119, 290)]
        for point in white_points:
            cv2.circle(debug_image, point, 5, (255, 255, 0), -1) # 白色圆点标记
            cv2.putText(debug_image, f"({converter.pixel_to_world(point)[0]:.2f}, {converter.pixel_to_world(point)[1]:.2f})",
                        (point[0]+10, point[1]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            print(converter.pixel_to_world(point))
            

        for point in white_points:
            cv2.circle(debug_image, point, 5, (255, 255, 255), -1) # 白色圆点标记


    cv2.imshow("ArUco XY Coordinate System Debug", debug_image)
    print("按任意键退出...")
    cv2.waitKey(0) # 等待按键后退出 (在实际应用中，这里是cv2.waitKey(1) & 0xFF == ord('q'))

    # if cap: cap.release() # 在实际应用中
    cv2.destroyAllWindows()