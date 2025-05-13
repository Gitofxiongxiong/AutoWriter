import subprocess
import time
import os
import re
from turtle import screensize
from PIL import Image
import io
import platform
import threading
from cache import get_cache
import cv2
# 使用临时文件作为中间存储
import tempfile


class CameraController:
    def __init__(self):
        # 基础配置
        self.device_id = None
        self.camera_package = "com.android.camera"
        self.camera_activity = "com.android.camera.Camera"
        self.shutter_keycode = "27"  # KEYCODE_CAMERA (27)
        self.device_photo_root_dir = "/sdcard/DCIM"
        self.pulled_photo_dir = "./captured_photos"
        self.screen_timeout_always_on = 2147483647
        self.screen_timeout_normal = 3600000  # 1小时
        self.lock_after_timeout_long = 86400000  # 24小时
        self.lock_after_timeout_normal = 3600000  # 1小时
        
        # 相机状态
        self.is_camera_open = False
        self.last_photo_time = 0
        self.camera_idle_timeout = 300  # 5分钟无操作自动关闭相机
        self.camera_monitor_thread = None
        self.stop_monitor = False

        # 初始化输出目录
        os.makedirs(self.pulled_photo_dir, exist_ok=True)

        # 系统检查
        self._check_system_requirements()

        # 添加缓存系统
        
        self.cache = get_cache()

        # 添加照片ID管理
        self.photo_ids = []  # 存储所有照片ID的列表
        self.max_photo_history = 100  # 最多保存最近100张照片的ID

    def _check_system_requirements(self):
        """检查系统要求"""
        if platform.system().lower() != "windows":
            raise RuntimeError("此相机控制器仅支持Windows系统")
        
        # 检查ADB是否可用
        try:
            subprocess.run(['adb', 'version'], capture_output=True, check=True)
        except FileNotFoundError:
            raise RuntimeError("未找到ADB。请确保ADB已安装并添加到系统PATH中")
        except subprocess.CalledProcessError:
            raise RuntimeError("ADB命令执行失败，请检查ADB安装状态")

    def _run_adb_command(self, command_list, check_rc=True, timeout=15, return_output=True, is_shell=True, is_binary_output=False):
        """执行ADB命令"""
        base_cmd = ["adb"]
        if self.device_id:
            base_cmd.extend(["-s", self.device_id])

        if is_shell and command_list[0] != "shell":
            full_cmd = base_cmd + ["shell"] + command_list
        else:
            full_cmd = base_cmd + command_list

        try:
            if return_output:
                process = subprocess.run(full_cmd, capture_output=True, check=False, timeout=timeout)
                stdout_data = process.stdout
                stderr_data = process.stderr
                if not is_binary_output:
                    stdout_str = stdout_data.decode('utf-8', errors='replace').strip() if stdout_data else ""
                    stderr_str = stderr_data.decode('utf-8', errors='replace').strip() if stderr_data else ""
                else:
                    stdout_str = stdout_data
                    stderr_str = stderr_data.decode('utf-8', errors='replace').strip() if stderr_data else ""
            else:
                process = subprocess.run(full_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                      check=False, timeout=timeout)
                stdout_str = None
                stderr_str = None

            if check_rc and process.returncode != 0:
                return None, stderr_str, process.returncode
            return stdout_str, stderr_str, process.returncode
        except Exception as e:
            print(f"执行ADB命令时发生错误: {e}")
            return None, str(e), -1

    def connect_device(self):
        """连接设备并选择第一个可用设备"""
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise RuntimeError(f"获取设备列表失败: {result.stderr.strip()}")
            
            devices = []
            lines = result.stdout.strip().splitlines()
            if len(lines) > 1:  # 第一行是标题
                for line in lines[1:]:
                    parts = line.strip().split("\t")
                    if len(parts) == 2 and parts[1] == "device":
                        devices.append(parts[0])
            
            if not devices:
                raise RuntimeError("未找到已连接的设备")
            
            if len(devices) > 1:
                print("警告：检测到多个设备，将使用第一个设备")
                
            self.device_id = devices[0]
            print(f"已连接设备: {self.device_id}")
            return True
            
        except Exception as e:
            print(f"连接设备失败: {e}")
            return False

    def is_screen_on(self):
        """检查屏幕是否点亮"""
        stdout, _, rc = self._run_adb_command(["dumpsys", "power"])
        if rc == 0 and stdout:
            for line in stdout.splitlines():
                
                if "mWakefulness=" in line or "mWakefulnessRaw=" in line:
                    
                    state = line.split("=")[-1].strip().lower()
                    print(f"屏幕状态: {state}")
                    return state in ["awake", "dreaming"]
                if "Display Power: state=" in line:
                    state = line.split("=")[-1].strip().upper()
                    print(f"屏幕状态: {state}")
                    return state in ["ON", "DOZE", "DOZE_SUSPEND"]
        return False

    def is_screen_locked(self):
        """检查屏幕是否锁定"""
        screenshot_bytes = self._take_screenshot_to_memory()
        if not screenshot_bytes:
            return True
        return self._is_image_effectively_black(screenshot_bytes)

    def _take_screenshot_to_memory(self):
        """获取屏幕截图"""
        png_data, stderr_str, rc = self._run_adb_command(
            ["exec-out", "screencap", "-p"],
            is_shell=False,
            is_binary_output=True,
            check_rc=False
        )
        if png_data:
            if os.name == 'nt':
                if png_data.startswith(b'\r\n'): png_data = png_data[2:]
                elif png_data.startswith(b'\n'): png_data = png_data[1:]
            return png_data
        return None
    # 有息屏显示时大约的平均像素值是4左右
    def _is_image_effectively_black(self, image_bytes, threshold=25):
        """判断图像是否接近全黑"""
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert('L')
            pixels = list(img.getdata())
            if not pixels:
                return True
            avg_pixel = sum(pixels) / len(pixels)
            print(f"平均像素值: {avg_pixel}")
            return avg_pixel < threshold
        except Exception as e:
            print(f"分析图像亮度失败: {e}")
            return True
    def _get_screen_size(self):
        """获取设备屏幕尺寸"""
        stdout, _, rc = self._run_adb_command(["wm", "size"])
        if rc == 0 and stdout:
            match = re.search(r"Physical size: (\d+)x(\d+)", stdout)
            if match:
                width, height = int(match.group(1)), int(match.group(2))
                return width, height
        return 1080, 1920  # 默认尺寸   

    def wake_and_unlock_screen(self, unlock_callback=None):
        """
        唤醒并解锁屏幕
        
        Args:
            unlock_callback: 可选的回调函数，当屏幕解锁后会被调用
        """
        # if not self.is_screen_on():
        #     print("点亮屏幕中。。。。")
        #     self._run_adb_command(["input", "keyevent", "224"], return_output=False)  # KEYCODE_WAKEUP
        #     time.sleep(0.5)
        #     print("屏幕点亮结束")
        #     # 尝试多种方式唤醒屏幕
        #     # 1. 先使用电源键
        #     # self._run_adb_command(["input", "keyevent", "26"], return_output=False)  # KEYCODE_POWER
        #     # time.sleep(1)
            
        #     # # 2. 如果屏幕仍未点亮，尝试使用WAKEUP命令
        #     # if not self.is_screen_on():
        #     #     self._run_adb_command(["input", "keyevent", "224"], return_output=False)  # KEYCODE_WAKEUP
        #     #     time.sleep(1)
            
        #     # # 3. 如果仍未点亮，尝试使用HOME键
        #     # if not self.is_screen_on():
        #     #     self._run_adb_command(["input", "keyevent", "3"], return_output=False)  # KEYCODE_HOME
        #     #     time.sleep(1)


        '''
        模拟上划屏幕:
            屏幕中心 X 坐标: 1080 / 2 = 540
            起始 Y 坐标 (y1): 1920 * 0.8 = 1536 (屏幕下方)
            结束 Y 坐标 (y2): 1920 * 0.2 = 384 (屏幕上方)
            持续时间 (可选): 300 毫秒
        '''
        self._run_adb_command(
            ["input", "swipe", "540", "1536", "540", "384", "300", "300"],
            return_output=False
        )
        time.sleep(1)  # 等待动画完成

        
        # 检查屏幕是否锁定
        if self.is_screen_locked():
            print("检测到屏幕锁定，请手动解锁设备")
            if unlock_callback:
                unlock_callback()
            else:
                input("解锁后按Enter继续...")

        # 设置屏幕超时和锁屏时间
        self._run_adb_command(
            ["settings", "put", "system", "screen_off_timeout", str(self.screen_timeout_always_on)],
            return_output=False
        )
        self._run_adb_command(
            ["settings", "put", "secure", "lock_screen_after_timeout", str(self.lock_after_timeout_long)],
            return_output=False
        )

    def _start_camera_monitor(self):
        """启动相机监控线程"""
        def monitor():
            while not self.stop_monitor:
                if self.is_camera_open and time.time() - self.last_photo_time > self.camera_idle_timeout:
                    self.close_camera()
                time.sleep(60)  # 每分钟检查一次

        self.camera_monitor_thread = threading.Thread(target=monitor, daemon=True)
        self.camera_monitor_thread.start()

    def open_camera(self):
        """打开相机应用"""
        if not self.is_camera_open:
            self._run_adb_command(
                ["am", "start", "-n", f"{self.camera_package}/{self.camera_activity}"],
                return_output=False
            )
            time.sleep(3)
            self.is_camera_open = True
            self.last_photo_time = time.time()

            # 启动监控线程（如果未启动）
            if not self.camera_monitor_thread or not self.camera_monitor_thread.is_alive():
                self.stop_monitor = False
                self._start_camera_monitor()

    def close_camera(self):
        """关闭相机应用"""
        if self.is_camera_open:
            self._run_adb_command(["am", "force-stop", self.camera_package], return_output=False)
            self.is_camera_open = False

    def take_photo(self):
        """拍照并获取照片"""
        if not self.is_camera_open:
            self.open_camera()

        # 发送快门键
        self._run_adb_command(["input", "keyevent", self.shutter_keycode], return_output=False)
        time.sleep(2)  # 等待照片保存
        self.last_photo_time = time.time()

        # 获取最新照片并返回图片ID
        return self._pull_latest_photo()

    def _pull_latest_photo(self):
        """获取最新拍摄的照片"""
        # 查找最新照片
        find_cmd = (
            f"find {self.device_photo_root_dir} -type f "
            r"\( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.heic' -o -iname '*.webp' -o -iname '*.dng' \) "
            r"-printf '%T@ %p\n' 2>/dev/null "
            r"| sort -nr "
            r"| head -n 1 "
            r"| cut -d' ' -f2-"
        )
        stdout, _, rc = self._run_adb_command([find_cmd], timeout=20)
        if rc != 0 or not stdout:
            print("未能找到最新照片")
            return None

        device_path = stdout.strip()
        filename = os.path.basename(device_path)
        if not filename:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"photo_{timestamp}.jpg"

        # 使用临时文件作为中间存储
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
            temp_path = temp_file.name
        
        try:
            # 将文件拉取到临时文件
            _, _, rc = self._run_adb_command(
                ["pull", device_path, temp_path],
                is_shell=False,
                return_output=False,
                timeout=60
            )
            
            if rc == 0 and os.path.exists(temp_path):
                # 读取临时文件内容
                with open(temp_path, 'rb') as f:
                    image_data = f.read()
                    
                # 生成唯一的图片ID
                image_id = f"{int(time.time())}_{filename}"
                
                # 保存到缓存
                metadata = {
                    "original_filename": filename,
                    "device_path": device_path,
                    "capture_time": time.time()
                }
                
                print(f"保存图片到缓存: {image_id}, 图像大小: {len(image_data)} 字节")
                if self.cache.save_image(image_id, image_data, metadata=metadata):
                    # 添加新的照片ID到列表
                    print("保存成功")
                    self.photo_ids.append(image_id)
                    # 如果超出最大历史记录数，移除最旧的
                    if len(self.photo_ids) > self.max_photo_history:
                        self.photo_ids.pop(0)
                    return image_id
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        return None
      

    def get_latest_photo_id(self):
        """获取最近一张照片的ID
        
        Returns:
            str: 最近一张照片的ID，如果没有照片则返回None
        """
        return self.photo_ids[-1] if self.photo_ids else None

    def get_all_photo_ids(self):
        """获取所有已存储照片的ID列表
        
        Returns:
            list: 所有照片ID的列表，按时间顺序排列（最新的在最后）
        """
        return self.photo_ids.copy()

    def __del__(self):
        """清理资源"""
        self.stop_monitor = True
        if self.camera_monitor_thread:
            self.camera_monitor_thread.join(timeout=1)
        if self.is_camera_open:
            self.close_camera()
        # 恢复正常的屏幕超时设置
        try:
            self._run_adb_command(
                ["settings", "put", "system", "screen_off_timeout", str(self.screen_timeout_normal)],
                return_output=False
            )
            self._run_adb_command(
                ["settings", "put", "secure", "lock_screen_after_timeout", str(self.lock_after_timeout_normal)],
                return_output=False
            )
        except:
            pass

# 创建默认实例
default_cam_ctr = CameraController()
# 导出便捷函数
def get_cam_ctr() -> CameraController:
    """获取默认缓存实例"""
    return default_cam_ctr


if __name__ == "__main__":
    # 创建控制器实例
    camera = get_cam_ctr()
    def on_unlock_needed():
        # 这里实现通知逻辑，例如：
        input("调用毁掉函数进行解锁...")

    # 或者发送通知到前端界面等
    # 连接设备
    if camera.connect_device():
        # 确保屏幕亮起且解锁
        camera.wake_and_unlock_screen(unlock_callback=on_unlock_needed)
        
        # 拍照并获取照片路径
        photo_path = camera.take_photo()
        if photo_path:
            print(f"照片已保存到: {photo_path}")

        latest_id = camera.get_latest_photo_id()
        pic = get_cache().get_image_cv2(latest_id)
        if pic is not None:
            print(f"图像类型: {type(pic)}")
            print(f"图像形状: {pic.shape if hasattr(pic, 'shape') else '无形状'}")
        cv2.imshow("pic", pic)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
