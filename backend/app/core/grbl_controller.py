import serial
import serial.tools.list_ports
import time
import re

# 单位固定位mm
# 右手坐标系
class GRBLController:
    def __init__(self, default_port="COM3", default_baudrate=115200):
        self.ser = None
        self.port = default_port
        self.baudrate = default_baudrate
        self.connected = False
        self.status_message = "未连接"
        self.is_pen_down = False

        # 内部维护的坐标 (优先相机，其次GRBL)
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_z = 0.0 # GRBL的Z，笔的抬起落下可能映射到特定Z值或M代码

        self.camera_override_active = False # 标记是否正在使用相机坐标

        # XY平面可移动范围
        self.min_x = -10.0
        self.max_x = 10.0
        self.min_y = -10.0
        self.max_y = 10.0

        # 移动步长。33
    
        self.step_size_xy = 1.0  # mm
        self.step_size_z = 0.5 # mm (如果Z轴用于精细高度控制)

        # Z轴落笔方向 (True: 正方向为落笔, False: 负方向为落笔)
        # 这通常意味着Z值变大是落笔还是变小是落笔。
        # 或者，我们可以定义笔的抬起和落下对应的绝对Z坐标。
        self.z_pen_down_value = -2.0 # Z轴落笔的目标绝对坐标 (示例)
        self.z_pen_up_value = 0.0    # Z轴抬笔的目标绝对坐标 (示例)
        # 或者使用一个标志位来反转M命令或Z移动方向
        self.z_direction_down_is_positive = False # 假设Z轴向下为负值

        self.grbl_buffer = [] # 用于存储GRBL的响应

        # 尝试连接默认端口
        self.connect(self.port)
        print(f"初始化完成，连接状态: {self.connected}")

        

    def _send_ser_msg(self, msg, wait_for_response=True, timeout=5):
        """
        内部函数，发送消息到串口，用于在确认连接前给写字机发送消息
        
        Args:
            msg: 要发送的消息
            wait_for_response: 是否等待响应，默认为True
            timeout: 等待响应的超时时间（秒），默认为5秒
            
        Returns:
            dict: 包含状态和数据的字典
                {
                    'success': bool,  # 操作是否成功
                    'data': list,     # 接收到的响应列表（如果有）
                    'error': str      # 错误信息（如果有）
                }
        """
        result = {
            'success': False,
            'data': [],
            'error': None
        }
        
        if not self.ser or not self.ser.is_open:
            result['error'] = "串口未连接或未打开"
            return result
            
        try:
            self.ser.reset_input_buffer()  # 清除输入缓存
            self.ser.write((msg + '\n').encode('utf-8'))
            
            # 模式1：不等待响应，直接返回成功
            if not wait_for_response:
                result['success'] = True
                return result
            
            # 模式2：等待响应，带超时
            start_time = time.time()
            
            while True:
                # 检查是否超时
                if time.time() - start_time > timeout:
                    result['error'] = f"等待响应超时（{timeout}秒）"
                    return result
                
                # 检查是否有数据可读
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()
                    result['data'].append(line)
                    
                    if line == 'ok':
                        result['success'] = True
                        return result
                    elif line == 'error':
                        result['error'] = "GRBL命令测试失败"
                        return result
                    # 继续读取，直到收到 'ok' 或 'error'
                
                # 短暂休眠，避免CPU占用过高
                time.sleep(0.01)
                
        except serial.SerialException as e:
            result['error'] = f"串口错误: {e}"
            self.disconnect()
            return result

    def _send_grbl_command(self, cmd, quiet=False, wait_for_ok=True, timeout=5):
        if not self.connected or not self.ser:
            if not quiet:
                print("错误：设备未连接。")
            return None

        try:
            self.ser.reset_input_buffer() # 清除输入缓存
            self.ser.write((cmd + '\n').encode('utf-8'))
            if not quiet:
                print(f"发送: {cmd}")

            if wait_for_ok:
                responses = []
                start_time = time.time()
                while True:
                    if self.ser.in_waiting > 0:
                        line = self.ser.readline().decode('utf-8').strip()
                        if not quiet:
                            print(f"接收: {line}")
                        responses.append(line)
                        if 'ok' in line or 'error' in line:
                            # 如果是状态查询，我们需要解析位置
                            self._parse_status_report(responses)
                            return responses
                    if time.time() - start_time > timeout:
                        if not quiet:
                            print(f"错误：等待GRBL响应 '{cmd}' 超时。")
                        return ["error:timeout"] + responses # 返回错误信息和已收到的响应
                return responses # Fallback, should be covered by timeout
            else:
                time.sleep(0.1) # 短暂等待，确保命令已发送
                # 即使不等待ok，也尝试读取一下，避免缓冲区填满
                
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()
                    if not quiet:
                        print(f"接收 (no wait): {line}")
                    self._parse_status_report([line]) # 尝试解析
                return ["sent"] # 表示已发送
        except serial.SerialException as e:
            if not quiet:
                print(f"串口错误: {e}")
            self.disconnect()
            return None
        except Exception as e:
            if not quiet:
                print(f"发送命令时发生未知错误: {e}")
            return None

    def _parse_status_report(self, responses):
        """解析GRBL的状态报告，特别是MPos"""
        # 示例: <Idle|MPos:10.000,20.000,-1.000|FS:0,0|WCO:0.000,0.000,0.000>
        # 示例: <Run|MPos:10.123,20.456,-1.000|FS:500,0>
        for resp_line in responses:
            if 'MPos:' in resp_line:
                match = re.search(r"MPos:([-\d\.]+),([-\d\.]+),([-\d\.]+)", resp_line)
                if match:
                    self.current_x = float(match.group(1))
                    self.current_y = float(match.group(2))
                    self.current_z = float(match.group(3))

                    return True
        return False

    # 1. 查看当前有多少可以连接的com口，并返回
    def list_available_ports(self):
        ports = serial.tools.list_ports.comports()
        available_ports = [port.device for port in ports]
        if not available_ports:
            print("未找到可用的COM端口。")
        return available_ports

    # 2. 设置波特率，默认波特率是115200
    def set_baudrate(self, baudrate):
        if self.connected:
            print("错误：请先断开连接再设置波特率。")
            return
        try:
            self.baudrate = int(baudrate)
            print(f"波特率已设置为: {self.baudrate}")
        except ValueError:
            print("错误：无效的波特率值。")

    # 3. 连接已选择的端口
    def connect(self, port):
        if self.connected:
            print("设备已连接。")
            return True
        try:
            self.ser = serial.Serial(port, self.baudrate, timeout=1)
            time.sleep(2) # 等待GRBL初始化
            if not self.ser:
                print("错误：未能打开串口。")
                return False

            self.ser.flushInput()
            self.ser.flushOutput()

            # 发送一个软复位或唤醒字符 (GRBL通常在连接后需要一个换行符或Ctrl-X)
            self._send_ser_msg("\r\n\r\n", wait_for_response="false") # 发送几个换行符尝试唤醒
            time.sleep(0.5)
            self.ser.flushInput() # 清空可能的回显

            # 尝试发送一个简单的命令并检查响应
            initial_status = self._send_ser_msg("?") # 查询状态
            print(f"初始状态: {initial_status}")
            if initial_status and initial_status['success']:
                self.connected = True
                self.status_message = f"已连接到 {port}，波特率 {self.baudrate}"
                print(self.status_message)
                self.set_units_to_mm() # 确保单位是mm
                self._send_grbl_command("G90", quiet=False) # 设置为绝对坐标模式
                self.query_grbl_position() # 获取初始位置
                return True
            else:
                self.ser.close()
                self.ser = None
                self.connected = False
                self.status_message = f"连接失败: {port} (无有效响应)"
                print(self.status_message)
                if initial_status:
                    print(f"失败时的响应: {initial_status}")
                return False

        except serial.SerialException as e:
            self.connected = False
            self.status_message = f"连接失败: {e}"
            print(self.status_message)
            if self.ser:
                self.ser.close()
                self.ser = None
            return False

    def disconnect(self):
        if self.ser and self.ser.is_open:
            try:
                # 在关闭前尝试让GRBL进入空闲状态，避免操作中途断开
                self._send_grbl_command("!", quiet=True, wait_for_ok=False) # Feed Hold
                time.sleep(0.1)
                self._send_grbl_command("M5", quiet=True, wait_for_ok=False) # Spindle Off (Pen Up if controlled by spindle)
                time.sleep(0.1)
                self._send_grbl_command("$X", quiet=True, wait_for_ok=False) # Unlock
                self.ser.close()
            except Exception as e:
                print(f"关闭串口时发生错误: {e}")
        self.ser = None
        self.connected = False
        self.status_message = "未连接"
        print("连接已断开。")

    # 4. 查询当前的连接状态
    def get_connection_status(self):
        return self.connected, self.status_message

    # 5. 设备的移动单位都设置为mm
    def set_units_to_mm(self):
        response = self._send_grbl_command("G21", quiet=False) # G21 for millimeters
        if response and 'ok' in response[-1]:
            print("单位已设置为毫米 (mm)。")
        else:
            print("设置单位为毫米失败。")

    # 5.1 (补充) 设置XY平面的可移动范围
    def set_xy_movable_range(self, min_x, max_x, min_y, max_y):
        """
        设置XY平面的可移动范围，并检查当前位置是否在新范围内
        
        Args:
            min_x: X轴最小值
            max_x: X轴最大值
            min_y: Y轴最小值
            max_y: Y轴最大值
            
        Returns:
            bool: 设置是否成功
        """
        # 获取当前位置
        current_x, current_y, _ = self.get_current_position()
        
        # 检查当前位置是否在新设置的范围内
        if not (min_x <= current_x <= max_x and min_y <= current_y <= max_y):
            print(f"错误：当前位置 X={current_x}, Y={current_y} 不在设置的可移动范围 X({min_x}-{max_x}), Y({min_y}-{max_y})内。")
            print(f"设置失败：请先将机器移动到有效范围内，或调整范围以包含当前位置。")
            return False
            
        # 当前位置在范围内，设置成功
        self.min_x, self.max_x, self.min_y, self.max_y = min_x, max_x, min_y, max_y
        print(f"可移动范围已设置为: X({self.min_x} to {self.max_x}), Y({self.min_y} to {self.max_y})")
        return True

    def _is_within_xy_bounds(self, x, y):
        if not (self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y):
            #print(f"警告：目标位置 X={x}, Y={y} 超出可移动范围 X({self.min_x}， {self.max_x}), Y({self.min_y}， {self.max_y})。")
            return False
        return True

    # 5.2 (补充) 更新相机坐标 (由外部调用)
    def update_position_from_camera(self, x, y, z=None):
        """优先使用相机坐标更新当前位置"""
        self.current_x = x
        self.current_y = y
        if z is not None:
            self.current_z = z
        self.camera_override_active = True
        print(f"相机坐标更新: X={self.current_x}, Y={self.current_y}, Z={self.current_z}")

    def disable_camera_override(self):
        """停止使用相机坐标，回退到GRBL计算的坐标 (下次GRBL报告位置时更新)"""
        self.camera_override_active = False
        print("相机坐标覆盖已禁用，将使用GRBL报告的位置。")
        self.query_grbl_position() # 立即用GRBL的更新一次

    # 6. 提供xy平面上单步移动的接口，步长可设置
    def move_xy_step(self, dx=0, dy=0, force=False):
        target_x = self.current_x + dx * self.step_size_xy
        target_y = self.current_y + dy * self.step_size_xy
        is_within_xy_bounds = self._is_within_xy_bounds(target_x, target_y)

        if not is_within_xy_bounds and not force:
            return False
        if not is_within_xy_bounds and force:
            print("警告：目标位置超出可移动范围，但强制执行。")
        # G90表示绝对坐标, G91表示相对坐标。
        # 为了简单，我们直接用绝对坐标移动到计算出的新位置。
        # 或者，如果GRBL能很好地处理相对移动，可以先G91，移动，再G90。
        # 这里我们发送绝对坐标。
        cmd = f"G90 G0 X{target_x:.3f} Y{target_y:.3f}" # 使用G0快速移动
        response = self._send_grbl_command(cmd)
        if response and 'ok' in response[-1]:
            self.current_x = target_x
            self.current_y = target_y
            return True
        return False

        
    # 7. 可以查询当前设置的移动步长，并能修改
    def get_step_size_xy(self):
        return self.step_size_xy

    def set_step_size_xy(self, size):
        try:
            self.step_size_xy = float(size)
            print(f"XY移动步长已设置为: {self.step_size_xy} mm")
        except ValueError:
            print("错误：无效的步长值。")

    # 8. z轴是用于控制笔的抬起和落下
    def _move_z(self, target_z):
        """内部函数，移动Z轴到指定绝对位置"""
        cmd = f"G90 G0 Z{target_z:.3f}"
        response = self._send_grbl_command(cmd)
        if response and 'ok' in response[-1]:
            self.current_z = target_z # 更新Z轴位置
            print(f"Z轴已移动到: {target_z:.3f}")
            return True
        print(f"Z轴移动失败。响应: {response}")
        return False
    def pen_down(self):
        """落笔操作"""
        # target_z = self.current_z - self.z_pen_delta if self.z_direction_down_is_positive else self.current_z + self.z_pen_delta
        # 使用绝对坐标更可靠
        print("执行落笔...")
        res = self._move_z(self.z_pen_down_value)
        if res:
            self.is_pen_down = True
        return res
    def pen_up(self):
        """抬笔操作"""
        # target_z = self.current_z + self.z_pen_delta if self.z_direction_down_is_positive else self.current_z - self.z_pen_delta
        print("执行抬笔...")
        res = self._move_z(self.z_pen_up_value)
        if res:
            self.is_pen_down = False
        return res
    def set_pen_z_values(self, down_value, up_value):
        """设置落笔和抬笔的Z轴绝对坐标"""
        try:
            self.z_pen_down_value = float(down_value)
            self.z_pen_up_value = float(up_value)
            print(f"落笔Z值设置为: {self.z_pen_down_value}, 抬笔Z值设置为: {self.z_pen_up_value}")
        except ValueError:
            print("错误：无效的Z轴值。")
    def get_pen_z_values(self):
        """获取落笔和抬笔的Z轴绝对坐标"""
        return self.z_pen_down_value, self.z_pen_up_value
    
    
    # 9. 查询当前位置的接口
    def get_current_position(self):
        """返回由控制器维护的当前位置 (可能来自相机或GRBL)"""
        return self.current_x, self.current_y, self.current_z

    def query_grbl_position(self):
        """向GRBL查询当前位置并更新内部GRBL坐标 (如果相机覆盖未激活)"""
        response = self._send_grbl_command("?", quiet=True) # '?'是状态查询命令
        if response:
            if not self._parse_status_report(response): #尝试解析
                 print("查询GRBL位置：未能从响应中解析位置。")
        else:
            print("查询GRBL位置失败，无响应。")
        return self.current_x, self.current_y, self.current_z


    # 10. 提供gcode执行器
    def _check_gcode_bounds(self, gcode_lines):
        """
        在执行前检查这个任务执行会不会超出可移动的范围。
        这是一个简化的检查，只检查G0/G1的X,Y绝对坐标。
        更复杂的G-code (如G2/G3圆弧，G91相对坐标) 需要更复杂的解析器。
        """
        temp_x, temp_y = self.current_x, self.current_y # 从当前位置开始模拟
        is_absolute_mode = True # 假设G90启动

        for line_num, line_content in enumerate(gcode_lines):
            line = line_content.strip().upper()
            if not line or line.startswith('(') or line.startswith('%'): # 跳过空行和注释
                continue

            if "G90" in line:
                is_absolute_mode = True
            elif "G91" in line:
                is_absolute_mode = False

            # 简化解析: 查找 G0, G1, G00, G01
            # (G0 X10 Y20 F300)
            match = re.search(r"G0?[01]\s+", line)
            if match:
                x_val, y_val = None, None
                x_match = re.search(r"X([-\d\.]+)", line)
                y_match = re.search(r"Y([-\d\.]+)", line)

                if x_match: x_val = float(x_match.group(1))
                if y_match: y_val = float(y_match.group(1))

                next_x, next_y = temp_x, temp_y

                if is_absolute_mode:
                    if x_val is not None: next_x = x_val
                    if y_val is not None: next_y = y_val
                else: # Relative mode
                    if x_val is not None: next_x += x_val
                    if y_val is not None: next_y += y_val
                
                if not self._is_within_xy_bounds(next_x, next_y):
                    print(f"G-code 边界检查失败：第 {line_num+1} 行 '{line_content.strip()}' 将导致超出范围。")
                    print(f"模拟位置: X={next_x}, Y={next_y}")
                    return False
                temp_x, temp_y = next_x, next_y # 更新模拟位置
        return True

    def execute_gcode(self, gcode_content):
        if isinstance(gcode_content, str):
            gcode_lines = gcode_content.strip().split('\n')
        elif isinstance(gcode_content, list):
            gcode_lines = gcode_content
        else:
            print("错误: G-code内容格式无效，应为字符串或列表。")
            return False

        if not self._check_gcode_bounds(gcode_lines):
            print("G-code 任务未执行，因超出可移动范围。请检查G-code或可移动范围设置。")
            return False

        print("开始执行G-code...")
        success_count = 0
        for i, line in enumerate(gcode_lines):
            line = line.strip()
            if not line or line.startswith('(') or line.startswith('%'): # 跳过空行和注释
                continue

            print(f"执行G-code行 {i+1}/{len(gcode_lines)}: {line}")
            response = self._send_grbl_command(line, quiet=True) # Gcode执行时可以安静点，只在出错时打印
            if not response or 'ok' not in response[-1].lower():
                print(f"错误：执行G-code行 '{line}' 失败。响应: {response}")
                # 可以选择停止或继续
                # self.soft_reset() # 发生错误时可以尝试软复位
                return False # 停止执行
            success_count +=1
            time.sleep(0.05) # 给GRBL一点处理时间，特别是对于短指令流

        print(f"G-code 执行完成。共成功执行 {success_count} 行有效指令。")
        self.query_grbl_position() # 执行完毕后更新一下位置
        return True

    # 11. 提供电机使能和失能的接口
    def enable_motors(self):
        # GRBL通常在发送运动指令时自动使能电机。
        # $1=255 可以保持电机始终使能 (禁用步进电机空闲延迟)。
        # M17 是 RepRap/Marlin 的命令，GRBL不直接支持。
        # 发送 $X (解锁/解除警报) 通常也会使能电机。
        print("尝试使能电机 (通过解除警报)...")
        response = self._send_grbl_command("$X") # Unlock/Kill Alarm Lock
        if response and 'ok' in response[-1]:
            print("电机已使能 (或已处于使能状态)。")
        else:
            print("使能电机命令可能未成功。")
        # 或者，设置$1=255来禁用空闲失能
        # self._send_command("$1=255")

    def disable_motors(self):
        # GRBL的电机失能通常通过 $SLP (休眠) 命令实现，如果固件支持。
        # 或者通过设置 $1 为一个较小的值 (例如 $1=25)，让电机在空闲25ms后失能。
        # M18 是 RepRap/Marlin 的命令。
        # 如果没有 $SLP, 可能无法立即显式失能，它们会在空闲超时后自动失能。
        print("尝试发送休眠指令使电机失能 (如果GRBL固件支持 $SLP)...")
        response_slp = self._send_grbl_command("$SLP")
        if response_slp and 'ok' in response_slp[-1]:
            print("休眠指令已发送。如果支持，电机将失能。")
        else:
            print("休眠指令 ($SLP) 可能不受支持或发送失败。电机可能在空闲后根据 $1 设置自动失能。")
            print("可以尝试设置 '$1=25' (电机空闲25ms后失能)")
            # self._send_command("$1=25")

    # 12. 提供设置当前位置的接口
    def set_current_position_as(self, x, y, z=None):
        """
        设置GRBL的当前工作坐标系原点 (G92)。
        这会告诉GRBL“你现在在(x,y,z)”，而不会实际移动机器。
        同时也会更新控制器内部的坐标。
        """
        cmd = f"G92 X{float(x):.3f} Y{float(y):.3f}"
        if z is not None:
            cmd += f" Z{float(z):.3f}"

        response = self._send_grbl_command(cmd)
        if response and 'ok' in response[-1]:
            self.current_x = float(x)
            self.current_y = float(y)
            if z is not None:
                self.current_z = float(z)

            print(f"GRBL当前位置已设置为: X={self.current_x}, Y={self.current_y}" + (f", Z={self.current_z}" if z is not None else ""))
            return True
        else:
            print(f"设置当前位置失败。响应: {response}")
            return False

    def soft_reset(self):
        """发送软复位命令 (Ctrl-X)"""
        if not self.connected or not self.ser:
            print("错误：设备未连接。")
            return
        try:
            print("发送软复位 (Ctrl-X)...")
            self.ser.write(b'\x18') # Ctrl-X character
            time.sleep(1) # 等待GRBL重启
            self.ser.flushInput()
            # GRBL 重启后会打印欢迎信息
            welcome_msg = self.ser.read_until(b"Grbl").decode('utf-8', errors='ignore')
            if "Grbl" in welcome_msg:
                print("GRBL软复位成功。")
                # 可能需要重新设置单位和模式
                self.set_units_to_mm()
                self._send_grbl_command("G90") # 绝对坐标
                self.query_grbl_position()
            else:
                print(f"软复位后未收到GRBL欢迎信息。接收到: {welcome_msg}")

        except Exception as e:
            print(f"软复位时发生错误: {e}")

    def get_grbl_settings(self):
        """查询并打印所有GRBL设置 ($$)"""
        response = self._send_grbl_command("$$")
        if response:
            print("GRBL 设置:")
            for line in response:
                if line.startswith("$") and "=" in line: # 过滤掉 'ok'
                    print(line)
        else:
            print("查询GRBL设置失败。")

# 创建默认实例
default_grbl = GRBLController()

# 定义一个函数，用于获取默认实例
def get_default_grbl():
    return default_grbl

# --- 使用示例 ---
if __name__ == "__main__":
    #初始化时尝试连接默认端口，连接失败需要手动重新连接
    controller = get_default_grbl()
    is_connected, status_message = controller.get_connection_status()
    if not is_connected:
        # 1. 列出端口
        ports = controller.list_available_ports()
        if not ports:
            print("没有找到COM口，请检查设备连接。")
            exit()
        print("可用的COM口:")
        for i, port in enumerate(ports, 1):
            print(f"{i}. {port}")

        # 2. 选择端口
        selected_port = input("请输入要连接的COM口编号 (例如 1 表示第一个端口): ")
        try:
            selected_port = ports[int(selected_port) - 1]
            if not selected_port:
                print("无效的端口号。")
                exit()
            if not controller.connect(selected_port):
                print(f"无法连接到 {selected_port}。程序退出。")
                exit()
            else:
                is_connected, status_message = controller.get_connection_status()
                print(status_message)
        except (ValueError, IndexError):
            print("无效的端口号。程序退出。")
            exit()

    # 单位已在连接时自动设为mm，这里可以设置可移动范围
    controller.set_xy_movable_range(min_x=0, max_x=200, min_y=0, max_y=150)

    # 查询初始位置
    x, y, z = controller.query_grbl_position() # 查询GRBL报告的位置
    print(f"从GRBL查询到的初始位置: X={x:.3f}, Y={y:.3f}, Z={z:.3f}")
    x_c, y_c, z_c = controller.get_current_position() # 获取控制器维护的位置
    print(f"控制器维护的初始位置: X={x_c:.3f}, Y={y_c:.3f}, Z={z_c:.3f}")

    # 设置和获取步长
    controller.set_step_size_xy(5) # 设置为5mm
    print(f"当前XY步长: {controller.get_step_size_xy()} mm")

    # 单步移动
    print("\n开始单步移动测试...")
    controller.move_xy_step(dx=-1, dy=0, force = True) # 向X正方向移动一个步长
    time.sleep(1) # 等待移动完成
    controller.move_xy_step(dx=0, dy=-1) # 向Y正方向移动一个步长
    time.sleep(1)
    x, y, z = controller.get_current_position()
    print(f"单步移动后位置: X={x:.3f}, Y={y:.3f}, Z={z:.3f}")

    exit()

    

    
    


    # (可选) 5.2 如果有相机数据，可以更新
    # controller.update_position_from_camera(10.5, 20.3)
    # x_cam, y_cam, z_cam = controller.get_current_position()
    # print(f"相机更新后的位置: X={x_cam:.3f}, Y={y_cam:.3f}, Z={z_cam:.3f}")
    # controller.disable_camera_override() # 测试完可以禁用


    # 6. 单步移动
    print("\n开始单步移动测试...")
    controller.move_xy_step(dx=1, dy=0) # 向X正方向移动一个步长
    time.sleep(1) # 等待移动完成
    controller.move_xy_step(dx=0, dy=1) # 向Y正方向移动一个步长
    time.sleep(1)
    x, y, z = controller.get_current_position()
    print(f"单步移动后位置: X={x:.3f}, Y={y:.3f}, Z={z:.3f}")

    # 8. Z轴笔控制
    print("\n开始Z轴画笔测试...")
    controller.set_pen_z_values(down_value=-5.0, up_value=0.0) # 设置Z轴落笔为-5mm，抬笔为0mm
    controller.pen_up()
    time.sleep(1)
    controller.pen_down()
    time.sleep(1)
    controller.pen_up()
    time.sleep(1)
    x, y, z = controller.get_current_position()
    print(f"画笔操作后位置: X={x:.3f}, Y={y:.3f}, Z={z:.3f}")


    # 12. 设置当前位置 (例如，手动移动到某个点后，将其设为新的(0,0))
    print("\n测试设置当前位置...")
    controller.set_current_position_as(x=0, y=0, z=0) # 将当前物理位置设为逻辑原点
    x, y, z = controller.get_current_position()
    print(f"设置新原点后位置: X={x:.3f}, Y={y:.3f}, Z={z:.3f}")
    controller.query_grbl_position() # 再次查询，GRBL的MPos应该也是0,0,0了
    x_grbl, y_grbl, z_grbl = controller.get_current_position()
    print(f"设置新原点后GRBL报告的位置: X={x_grbl:.3f}, Y={y_grbl:.3f}, Z={z_grbl:.3f}")

    # 移动到 (10,10)
    controller.move_xy_step(dx=2, dy=2) # 假设步长还是5, (2*5, 2*5) -> (10,10)
    time.sleep(1)


    # 10. G-code执行器测试
    print("\n开始G-code执行测试...")
    # 先回家 (G28是可选的，有些GRBL配置可能没有正确设置回家位置)
    # controller.execute_gcode("G28")
    # time.sleep(5)

    # 简单的G-code画一个正方形
    sample_gcode_ok = """
    G90 ; 绝对坐标
    G0 Z0 ; 抬笔 (假设Z=0是抬笔状态)
    G0 X10 Y10 F500 ; 快速移动到起点
    G1 Z-2 F100 ; 落笔 (假设Z=-2是落笔状态)
    G1 X50 Y10 F300 ; 画第一条边
    G1 X50 Y50
    G1 X10 Y50
    G1 X10 Y10
    G0 Z0 ; 抬笔
    G0 X0 Y0 ; 回到工作原点
    """
    controller.execute_gcode(sample_gcode_ok)
    time.sleep(2)

    # 超出范围的G-code (假设范围是0-200, 0-150)
    sample_gcode_fail = """
    G90
    G0 X250 Y100 ; 这个会超出X范围
    """
    print("\n测试超出范围的G-code...")
    controller.execute_gcode(sample_gcode_fail)
    time.sleep(1)


    # 11. 电机使能/失能 (效果取决于GRBL配置)
    print("\n测试电机控制...")
    controller.disable_motors() # 尝试失能
    time.sleep(1)
    controller.enable_motors()  # 尝试使能 (通常移动指令就会使能)
    time.sleep(1)

    # 断开连接
    controller.disconnect()