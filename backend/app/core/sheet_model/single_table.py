import cv2
import numpy as np
from typing import Dict, Any, List, Tuple
import copy
import json
from PIL import Image, ImageDraw, ImageFont
from app.core.cache import get_cache
class SingleTable:
    """
    处理照片中只含有一个表格且占满纸张的情况
    """
    
    def __init__(self, image_index: str, table_info: Dict[str, Any]):
        """
        初始化 SingleTable 类
        
        Args:
            image_index: 图片路径
            table_info: 表格信息，包含表格的位置、单元格信息等
        """
        self.image_index = image_index
        self.table_info = copy.deepcopy(table_info)  # 深拷贝，避免修改原始数据
        self.original_image = get_cache().get_image_cv2(self.image_index)
        
        if self.original_image is None:
            raise Exception(f"无法读取图片")
        
        # 保存旋转信息和透视变换矩阵
        self.rotation_angle = self.table_info.get("data", {}).get("angle", 0)
        self.rotation_matrix = None
        self.perspective_matrix = None
        
        # 矫正后的图片
        self.corrected_image = None
        
        # 处理图片
        self._process_image()
    
    def _process_image(self):
        """
        处理图片，包括旋转和透视变换
        """
        # 1. 根据 angle 字段进行旋转
        self._rotate_image()
        self._apply_rotation_transform()
        # 2. 找到表格的四个顶点
        table_corners = self._find_table_corners()
        print(f"表格的四个顶点坐标: {table_corners}")
        # 3. 进行透视变换
        self._perspective_transform(table_corners)
        
       # 再应用透视变换
        self._apply_perspective_transform()
    
    def _rotate_image(self):
        """
        根据 angle 字段旋转图片
        """
        if self.rotation_angle == 0:
            self.rotated_image = self.original_image.copy()
            return
        
        height, width = self.original_image.shape[:2]
        center = (width // 2, height // 2)
        
        # 计算旋转矩阵
        self.rotation_matrix = cv2.getRotationMatrix2D(center, self.rotation_angle, 1.0)
        
        # 计算旋转后的图像大小
        cos = np.abs(self.rotation_matrix[0, 0])
        sin = np.abs(self.rotation_matrix[0, 1])
        new_width = int((height * sin) + (width * cos))
        new_height = int((height * cos) + (width * sin))
        
        # 调整旋转矩阵
        self.rotation_matrix[0, 2] += (new_width / 2) - center[0]
        self.rotation_matrix[1, 2] += (new_height / 2) - center[1]
        
        # 执行旋转
        self.rotated_image = cv2.warpAffine(
            self.original_image, 
            self.rotation_matrix, 
            (new_width, new_height), 
            flags=cv2.INTER_LINEAR
        )
    
    def _find_table_corners(self) -> List[Tuple[int, int]]:
        """
        根据表格单元格信息找到表格的四个顶点，输入的单元格坐标顺序：左上，右上，右下，左下
        
        Returns:
            表格的四个顶点坐标，顺序为：左上、右上、右下、左下
        """
        # 获取表格信息
        tables_info = self.table_info.get("data", {}).get("prism_tablesInfo", [])
        if not tables_info:
            raise Exception("表格信息为空")
        
        # 获取第一个表格的单元格信息
        cell_infos = tables_info[0].get("cellInfos", [])
        if not cell_infos:
            raise Exception("单元格信息为空")
        
        # 收集所有单元格的四个角点坐标
        all_corners = []
        for cell in cell_infos:
            pos = cell.get("pos", [])
            if len(pos) == 4:  # 确保单元格有4个角点
                corners = []
                for point in pos:
                    x, y = point.get("x", 0), point.get("y", 0)
                    
                    # 如果图片已旋转，则需要转换坐标
                    if self.rotation_matrix is not None:
                        # 将点转换为列向量
                        point_array = np.array([x, y, 1])
                        # 应用旋转矩阵
                        rotated_point = np.dot(self.rotation_matrix, point_array)
                        x, y = rotated_point[0], rotated_point[1]
                    
                    corners.append((x, y))
                all_corners.append(corners)
        
        if not all_corners:
            # 如果无法获取单元格角点，回退到原来的方法
            return self._find_table_corners_fallback()
        
        # 找到最接近左上角的点
        height, width = self.rotated_image.shape[:2]
        top_left = min(
            [corners[0] for corners in all_corners],
            key=lambda p: np.sqrt((p[0])**2 + (p[1])**2)
        )
        
        # 找到最接近右上角的点
        top_right = min(
            [corners[1] for corners in all_corners],
            key=lambda p: np.sqrt((p[0] - width)**2 + (p[1])**2)
        )
        
        # 找到最接近左下角的点
        bottom_left = min(
            [corners[3] for corners in all_corners],
            key=lambda p: np.sqrt((p[0])**2 + (p[1] - height)**2)
        )
        
        # 找到最接近右下角的点
        bottom_right = min(
            [corners[2] for corners in all_corners],
            key=lambda p: np.sqrt((p[0] - width)**2 + (p[1] - height)**2)
        )
        
        # 返回四个顶点坐标
        return [
            (int(top_left[0]), int(top_left[1])),         # 左上
            (int(top_right[0]), int(top_right[1])),        # 右上
            
            (int(bottom_right[0]), int(bottom_right[1])), # 右下
            (int(bottom_left[0]), int(bottom_left[1])),   # 左下
            
        ]
    
    def _find_table_corners_fallback(self) -> List[Tuple[int, int]]:
        """
        备用方法：通过最大最小坐标找到表格的四个顶点
        
        Returns:
            表格的四个顶点坐标，顺序为：左上、右上、右下、左下
        """
        # 获取表格信息
        tables_info = self.table_info.get("data", {}).get("prism_tablesInfo", [])
        if not tables_info:
            raise Exception("表格信息为空")
        
        # 获取第一个表格的单元格信息
        cell_infos = tables_info[0].get("cellInfos", [])
        if not cell_infos:
            raise Exception("单元格信息为空")
        
        # 初始化最小和最大坐标
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        # 遍历所有单元格，找到表格的边界
        for cell in cell_infos:
            pos = cell.get("pos", [])
            for point in pos:
                x, y = point.get("x", 0), point.get("y", 0)
                
                # 如果图片已旋转，则需要转换坐标
                if self.rotation_matrix is not None:
                    # 将点转换为列向量
                    point_array = np.array([x, y, 1])
                    # 应用旋转矩阵
                    rotated_point = np.dot(self.rotation_matrix, point_array)
                    x, y = rotated_point[0], rotated_point[1]
                
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
        
        # 表格的四个顶点
        return [
            (int(min_x), int(min_y)),  # 左上
            (int(max_x), int(min_y)),   # 右上
            (int(max_x), int(max_y)),  # 右下
            (int(min_x), int(max_y)),  # 左下
           
        ]
    
    def _perspective_transform(self, corners: List[Tuple[int, int]]):
        """
        根据表格四个顶点进行透视变换
        
        Args:
            corners: 表格的四个顶点坐标，顺序为：左上、右上、右下、左下
        """
        # 将点转换为 numpy 数组
        src_points = np.float32(corners)
        
        # 计算目标图像的宽度和高度
        width = max(
            int(np.sqrt(np.sum((corners[1][0] - corners[0][0])**2 + (corners[1][1] - corners[0][1])**2))), # 上边
            int(np.sqrt(np.sum((corners[2][0] - corners[3][0])**2 + (corners[2][1] - corners[3][1])**2)))  # 下边
        )
        height = max(
            int(np.sqrt(np.sum((corners[0][0] - corners[3][0])**2 + (corners[0][1] - corners[3][1])**2))), # 左边
            int(np.sqrt(np.sum((corners[2][0] - corners[1][0])**2 + (corners[2][1] - corners[1][1])**2)))  # 右边
        )
        
        # 设置目标图像的四个顶点坐标
        dst_points = np.float32([
            [0, 0],           # 左上角
            [width, 0],        # 右上角
            [width, height],  # 右下角
            [0, height],      # 左下角
            
        ])
        
        # 计算透视变换矩阵
        self.perspective_matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        
        # 进行透视变换
        self.corrected_image = cv2.warpPerspective(
            self.rotated_image, 
            self.perspective_matrix, 
            (width, height)
        )
    
    def _transform_point(self, point: Tuple[int, int]) -> Tuple[int, int]:
        """
        将一个点从原始图像坐标系转换到透视变换后的坐标系
        
        Args:
            point: 原始图像中的点坐标，格式为 (x, y)
            
        Returns:
            transformed_point: 变换后的点坐标，格式为 (x, y)
        """
        # 将点转换为齐次坐标
        x, y = point
        point_homogeneous = np.array([x, y, 1], dtype=np.float32)
        
        # 应用透视变换矩阵
        transformed = np.dot(self.perspective_matrix, point_homogeneous)
        
        # 从齐次坐标转换回笛卡尔坐标
        transformed_x = transformed[0] / transformed[2]
        transformed_y = transformed[1] / transformed[2]
        
        return (int(transformed_x), int(transformed_y))
    
    def _update_coordinates(self):
        """
        根据旋转信息和透视变换矩阵，更新表格信息中的坐标
        """
        # 获取表格信息
        tables_info = self.table_info.get("data", {}).get("prism_tablesInfo", [])
        if not tables_info:
            return
        
        # 先应用旋转变换
        self._apply_rotation_transform()
        
        # 再应用透视变换
        self._apply_perspective_transform()
    
    def _apply_rotation_transform(self):
        """
        应用旋转变换到表格信息中的坐标
        """
        if self.rotation_matrix is None:
            return
            
        # 获取表格信息
        tables_info = self.table_info.get("data", {}).get("prism_tablesInfo", [])
        if not tables_info:
            return
            
        # 更新第一个表格的单元格信息
        for cell in tables_info[0].get("cellInfos", []):
            pos = cell.get("pos", [])
            
            for point in pos:
                x, y = point.get("x", 0), point.get("y", 0)
                
                # 将点转换为列向量
                point_array = np.array([x, y, 1])
                # 应用旋转矩阵
                rotated_point = np.dot(self.rotation_matrix, point_array)
                
                # 更新坐标
                point["x"] = rotated_point[0]
                point["y"] = rotated_point[1]
        
        # 更新 prism_wordsInfo 中的坐标
        words_info = self.table_info.get("data", {}).get("prism_wordsInfo", [])
        for word in words_info:
            pos = word.get("pos", [])
            
            for point in pos:
                x, y = point.get("x", 0), point.get("y", 0)
                
                # 将点转换为列向量
                point_array = np.array([x, y, 1])
                # 应用旋转矩阵
                rotated_point = np.dot(self.rotation_matrix, point_array)
                
                # 更新坐标
                point["x"] = rotated_point[0]
                point["y"] = rotated_point[1]
            
            # 更新单词的中心坐标
            if "x" in word and "y" in word:
                x, y = word["x"], word["y"]
                
                # 将点转换为列向量
                point_array = np.array([x, y, 1])
                # 应用旋转矩阵
                rotated_point = np.dot(self.rotation_matrix, point_array)
                
                # 更新坐标
                word["x"] = rotated_point[0]
                word["y"] = rotated_point[1]
    
    def _apply_perspective_transform(self):
        """
        应用透视变换到表格信息中的坐标
        """
        if self.perspective_matrix is None:
            return
            
        # 获取表格信息
        tables_info = self.table_info.get("data", {}).get("prism_tablesInfo", [])
        if not tables_info:
            return
            
        # 更新第一个表格的单元格信息
        for cell in tables_info[0].get("cellInfos", []):
            pos = cell.get("pos", [])
            
            for point in pos:
                x, y = point.get("x", 0), point.get("y", 0)
                
                # 应用透视变换
                transformed_x, transformed_y = self._transform_point((x, y))
                
                # 更新坐标
                point["x"] = transformed_x
                point["y"] = transformed_y
        
        # 更新 prism_wordsInfo 中的坐标
        words_info = self.table_info.get("data", {}).get("prism_wordsInfo", [])
        for word in words_info:
            pos = word.get("pos", [])
            
            for point in pos:
                x, y = point.get("x", 0), point.get("y", 0)
                
                # 应用透视变换
                transformed_x, transformed_y = self._transform_point((x, y))
                
                # 更新坐标
                point["x"] = transformed_x
                point["y"] = transformed_y
            
            # 更新单词的中心坐标
            if "x" in word and "y" in word:
                x, y = word["x"], word["y"]
                
                # 应用透视变换
                transformed_x, transformed_y = self._transform_point((x, y))
                
                # 更新坐标
                word["x"] = transformed_x
                word["y"] = transformed_y
    
    def get_corrected_image(self):
        """
        获取矫正后的图片
        
        Returns:
            矫正后的图片
        """
        return self.corrected_image

    def get_drawed_image(self):
        """
        获取已经绘制上表格的矫正后图片
        
        Returns:
            绘制了表格和文字的矫正后图片
        """
        # 绘制单元格信息到矫正后的图片上
        draw_image = self.corrected_image.copy()
        
        # 获取单元格信息
        tables_info = self.table_info.get("data", {}).get("prism_tablesInfo", [])
        if tables_info:
            cell_infos = tables_info[0].get("cellInfos", [])
            
            # 为每个单元格绘制边框
            for cell in cell_infos:
                pos = cell.get("pos", [])
                if len(pos) >= 4:
                    # 提取单元格的四个角点坐标
                    points = []
                    for point in pos:
                        x, y = int(point.get("x", 0)), int(point.get("y", 0))
                        points.append((x, y))
                    
                    # 绘制单元格边框
                    for i in range(4):
                        cv2.line(draw_image, points[i], points[(i+1)%4], (0, 255, 255), 3)
        
        # 绘制文字信息
        words_info = self.table_info.get("data", {}).get("prism_wordsInfo", [])
        if words_info:
            # 将 OpenCV 图像转换为 PIL 图像
            img_pil = Image.fromarray(cv2.cvtColor(draw_image, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)
            
            for word in words_info:
                # 获取文字内容
                text = word.get("word", "")
                if not text:
                    continue
                
                # 获取文字位置
                pos = word.get("pos", [])
                if len(pos) < 4:
                    continue
                
                # 计算文字的中心位置
                x_coords = [p.get("x", 0) for p in pos]
                y_coords = [p.get("y", 0) for p in pos]
                center_x = int(sum(x_coords) / len(x_coords))
                center_y = int(sum(y_coords) / len(y_coords))
                
                # 获取文字大小
                font_size = word.get("width", 16)
                
                # 加载中文字体
                try:
                    font = ImageFont.truetype("simhei.ttf", font_size)
                except:
                    # 如果找不到字体文件，使用默认字体
                    font = ImageFont.load_default()
                
                # 绘制文字边框
                points = []
                for point in pos:
                    x, y = int(point.get("x", 0)), int(point.get("y", 0))
                    points.append((x, y))
                
                for i in range(4):
                    cv2.line(draw_image, points[i], points[(i+1)%4], (255, 0, 0), 1)
                
                # 获取文字大小以计算偏移
                text_bbox = draw.textbbox((0, 0), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                # 绘制文字内容，考虑文字大小进行居中偏移
                draw.text(
                    (center_x - text_width//2, center_y - text_height//2),
                    text,
                    font=font,
                    fill=(0, 0, 255)  # RGB颜色
                )
            
            # 将 PIL 图像转换回 OpenCV 格式
            draw_image = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        
        return draw_image   
    def get_web_tdtr_data(self):
        """
        生成适合在 Web 前端使用 <tr><td> 标签绘制表格的数据结构
        
        Returns:
            Dict: 包含表格行列数据和单元格信息的字典，格式为：
            {
                'rows': 行数,
                'cols': 列数,
                'cells': 二维数组，每个元素包含单元格的详细信息
            }
        """
         # 获取表格信息
        tables_info = self.table_info.get("data", {}).get("prism_tablesInfo", [])
        if not tables_info:
            raise Exception("表格信息为空")
        
        # 获取第一个表格的信息
        table_info = tables_info[0]
        rows = table_info.get("yCellSize", 0)
        cols = table_info.get("xCellSize", 0)
        
        # 创建空表格结构
        cells = [[None for _ in range(cols)] for _ in range(rows)]
        
        # 创建单元格位置映射表
        cell_position_map = {}    

        # 填充表格数据，处理合并单元格
        for cell in table_info.get("cellInfos", []):
            # 计算单元格中心点
            pos = cell.get("pos", [])
            if len(pos) == 4:
                cell_center_x = (pos[0].get("x", 0) + pos[1].get("x", 0) + 
                                pos[2].get("x", 0) + pos[3].get("x", 0)) / 4
                
                # 遍历单元格覆盖的所有行列
                for row in range(cell.get("ysc", 0), cell.get("yec", 0) + 1):
                    for col in range(cell.get("xsc", 0), cell.get("xec", 0) + 1):
                        # 只在合并单元格的左上角设置内容
                        if row == cell.get("ysc", 0) and col == cell.get("xsc", 0):
                            # 查找对应的文字块
                            word_info = None
                            for word in self.table_info.get("data", {}).get("prism_wordsInfo", []):
                                if word.get("tableCellId") == cell.get("tableCellId") and "pos" in word:
                                    word_info = word
                                    break
                            
                            # 确定文本对齐方式
                            align = 'center'  # 默认居中对齐
                            
                            if word_info and "pos" in word_info and len(word_info["pos"]) == 4:
                                # 计算文字块中心点
                                word_center_x = (word_info["pos"][0].get("x", 0) + word_info["pos"][1].get("x", 0) + 
                                                word_info["pos"][2].get("x", 0) + word_info["pos"][3].get("x", 0)) / 4
                                
                                # 计算中心点距离
                                distance = abs(word_center_x - cell_center_x)
                                
                                if distance > 3:
                                    align = 'left' if word_center_x < cell_center_x else 'right'
                            
                            # 设置单元格信息
                            cells[row][col] = {
                                'isEditable': self.is_cell_editable(cell),  # 默认可编辑，实际应用中可能需要更复杂的逻辑
                                'isValid': True,
                                'tableCellId': cell.get("tableCellId", ""),
                                'originalText': cell.get("word", ""),
                                'text': "",
                                'rowSpan': cell.get("yec", 0) - cell.get("ysc", 0) + 1,
                                'colSpan': cell.get("xec", 0) - cell.get("xsc", 0) + 1,
                                'originalAlign': align,
                                'textAlign': 'center'
                            }
                            
                            # 添加单元格位置到映射表中
                            cell_position_map[cell.get("tableCellId", "")] = {"row": row, "col": col}
                        else:
                            # 合并单元格的非左上角部分
                            cells[row][col] = {
                                'isValid': False,
                                'tableCellId': cell.get("tableCellId", "")
                            }
        
        return {
            'rows': rows,
            'cols': cols,
            'tdtr_cells': cells,
        }


    def get_corrected_table_info(self):
        """
        获取矫正后的表格信息
        
        Returns:
            矫正后的表格信息
        """
        return self.table_info
    
    def save_corrected_image(self, output_path: str):
        """
        保存矫正后的图片
        
        Args:
            output_path: 输出路径
        """
        cv2.imwrite(output_path, self.corrected_image)

    def is_cell_editable(self, cell):
        """
        判断单元格是否可编辑
        
        Args:
            cell: 单元格对象，包含位置信息(pos)和单元格ID(tableCellId)
            
        Returns:
            bool: 返回True表示可编辑，False表示不可编辑
        """
        # 如果没有表格数据，默认返回可编辑
        if not self.table_info:
            return True
        
        # 计算单元格多边形面积
        cell_area = self._calculate_polygon_area(cell.get("pos", []))
        
        # 查找该单元格内的所有文字块（通过tableCellId匹配）
        words_in_cell = [
            w for w in self.table_info.get("data", {}).get("prism_wordsInfo", [])
            if w.get("tableCellId") == cell.get("tableCellId") and w.get("pos")
        ]
        
        # 如果没有找到文字块，默认返回可编辑
        if not words_in_cell:
            return True
        
        # 初始化变量：文字总面积和中心点坐标
        total_word_area = 0
        word_center_x = 0
        word_center_y = 0
        
        # 遍历所有文字块，计算总面积和中心点
        for word in words_in_cell:
            word_pos = word.get("pos", [])
            # 累加每个文字块的面积
            total_word_area += self._calculate_polygon_area(word_pos)
            
            # 计算当前文字块的中心点（四个角的平均值）
            center_x = sum(p.get("x", 0) for p in word_pos) / 4
            center_y = sum(p.get("y", 0) for p in word_pos) / 4
            
            # 累加中心点坐标用于计算平均值
            word_center_x += center_x
            word_center_y += center_y
        
        # 计算所有文字块的平均中心点
        word_center_x = word_center_x / len(words_in_cell)
        word_center_y = word_center_y / len(words_in_cell)
        
        # 计算单元格的中心点（四个角的平均值）
        cell_center_x = sum(p.get("x", 0) for p in cell.get("pos", [])) / 4
        cell_center_y = sum(p.get("y", 0) for p in cell.get("pos", [])) / 4
        
        # 判断文字是否居中（中心点距离小于3像素视为居中）
        is_centered = (abs(word_center_x - cell_center_x) < 3 and 
                      abs(word_center_y - cell_center_y) < 3)
        
        # 判断条件：
        # 1. 文字总面积不超过单元格面积的40%
        # 2. 文字不居中
        # 满足以上两个条件才可编辑（取反）
        return not (total_word_area > cell_area * 0.4 or is_centered)
    
    def _calculate_polygon_area(self, points):
        """
        计算多边形面积（使用鞋带公式）
        
        Args:
            points: 多边形的顶点坐标列表
            
        Returns:
            float: 多边形的面积
        """
        if not points or len(points) < 3:
            return 0
        
        area = 0
        n = len(points)
        
        for i in range(n):
            j = (i + 1) % n
            area += points[i].get("x", 0) * points[j].get("y", 0)
            area -= points[j].get("x", 0) * points[i].get("y", 0)
        
        return abs(area) / 2

if __name__ == "__main__":  
    # 加载表格信息
    with open("F:\\typewriter\\AutoWriter\\table.json", "r", encoding="utf-8") as f:
        table_info = json.load(f)

    # 创建 SingleTable 实例
    single_table = SingleTable("F:\\typewriter\\AutoWriter\\test_img.jpg", table_info)

    # 获取矫正后的图片和表格信息
    corrected_image = single_table.get_corrected_image()
    corrected_table_info = single_table.get_corrected_table_info()
    info = single_table.get_web_tdtr_data()
    
    # 绘制单元格信息到矫正后的图片上
    draw_image = corrected_image.copy()
    
    # 获取单元格信息
    tables_info = corrected_table_info.get("data", {}).get("prism_tablesInfo", [])
    output_path = "F:\\typewriter\\AutoWriter\\corrected_table_info.json"
    with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(tables_info, f, ensure_ascii=False, indent=4)
    if tables_info:
        cell_infos = tables_info[0].get("cellInfos", [])
        
        # 为每个单元格绘制边框
        for cell in cell_infos:
            pos = cell.get("pos", [])
            if len(pos) >= 4:
                # 提取单元格的四个角点坐标
                points = []
                for point in pos:
                    x, y = int(point.get("x", 0)), int(point.get("y", 0))
                    points.append((x, y))
                
                # 绘制单元格边框
                for i in range(4):
                    cv2.line(draw_image, points[i], points[(i+1)%4], (0, 255, 255), 3)
                
    # 在绘制文字的部分替换为
    # 绘制文字信息
    words_info = corrected_table_info.get("data", {}).get("prism_wordsInfo", [])
    if words_info:
        # 将 OpenCV 图像转换为 PIL 图像
        img_pil = Image.fromarray(cv2.cvtColor(draw_image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        
        for word in words_info:
            # 获取文字内容
            text = word.get("word", "")
            if not text:
                continue
            
            # 获取文字位置
            pos = word.get("pos", [])
            if len(pos) < 4:
                continue
            
            # 计算文字的中心位置
            x_coords = [p.get("x", 0) for p in pos]
            y_coords = [p.get("y", 0) for p in pos]
            center_x = int(sum(x_coords) / len(x_coords))
            center_y = int(sum(y_coords) / len(y_coords))
            
            # 获取文字大小
            font_size = word.get("width", 16)
            
            # 加载中文字体
            try:
                font = ImageFont.truetype("simhei.ttf", font_size)
            except:
                # 如果找不到字体文件，使用默认字体
                font = ImageFont.load_default()
            
            # 绘制文字边框
            points = []
            for point in pos:
                x, y = int(point.get("x", 0)), int(point.get("y", 0))
                points.append((x, y))
            
            for i in range(4):
                cv2.line(draw_image, points[i], points[(i+1)%4], (255, 0, 0), 1)
            
            # 获取文字大小以计算偏移
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # 绘制文字内容，考虑文字大小进行居中偏移
            draw.text(
                (center_x - text_width//2, center_y - text_height//2),
                text,
                font=font,
                fill=(0, 0, 255)  # RGB颜色
            )
        
        # 将 PIL 图像转换回 OpenCV 格式
        draw_image = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    
    # 显示绘制了单元格的图片
    cv2.imshow("Corrected Image with Cells", draw_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()