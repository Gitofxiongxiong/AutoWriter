import os
import time
import shutil
from datetime import datetime, timedelta
import diskcache as dc
import threading
import json
import base64
from typing import Any, Optional, Union, Dict, List
import cv2
import numpy as np

class CacheSystem:

    """
    基于diskcache的缓存系统，用于存储图片和结构化数据
    支持自动清理过期数据（默认1天）
    """

    def __init__(self, cache_dir: str = None, expire_days: int = 1):
        """
        初始化缓存系统
        
        参数:
            cache_dir: 缓存目录，默认为 F:/typewriter/AutoWriter/backend/app/cache_data
            expire_days: 过期时间（天），默认为1天
        """
        if cache_dir is None:
            cache_dir = os.path.abspath("F:/typewriter/AutoWriter/backend/app/cache_data")
        
        # 确保缓存目录存在
        os.makedirs(cache_dir, exist_ok=True)
        
        # 初始化diskcache
        self.cache = dc.Cache(cache_dir)
        self.expire_seconds = expire_days * 24 * 60 * 60
        
        # 启动自动清理线程
        self.cleanup_thread = threading.Thread(target=self._auto_cleanup, daemon=True)
        self.cleanup_thread.start()
    
    def set(self, key: str, value: Any, expire: int = None) -> bool:
        """
        存储数据到缓存
        
        参数:
            key: 缓存键
            value: 缓存值（可以是任何可序列化的对象）
            expire: 过期时间（秒），默认使用全局设置
            
        返回:
            bool: 是否成功
        """
        expire_time = expire if expire is not None else self.expire_seconds
        try:
            self.cache.set(key, value, expire=expire_time)
            return True
        except Exception as e:
            print(f"缓存设置失败: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        从缓存获取数据
        
        参数:
            key: 缓存键
            default: 如果键不存在，返回的默认值
            
        返回:
            缓存的值或默认值
        """
        try:
            return self.cache.get(key, default)
        except Exception as e:
            print(f"缓存获取失败: {e}")
            return default
    
    def delete(self, key: str) -> bool:
        """
        删除缓存中的数据
        
        参数:
            key: 缓存键
            
        返回:
            bool: 是否成功
        """
        try:
            return self.cache.delete(key)
        except Exception as e:
            print(f"缓存删除失败: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        检查键是否存在于缓存中
        
        参数:
            key: 缓存键
            
        返回:
            bool: 是否存在
        """
        return key in self.cache
    
    def save_image(self, image_id: str, image_data: Union[bytes, str], 
                  metadata: Dict = None, expire: int = None) -> bool:
        """
        保存图片到缓存
        
        参数:
            image_id: 图片ID
            image_data: 图片数据（二进制或base64字符串）
            metadata: 图片元数据
            expire: 过期时间（秒）
            
        返回:
            bool: 是否成功
        """
        try:
            # 如果是base64字符串，转换为二进制
            if isinstance(image_data, str):
                if image_data.startswith('data:image'):
                    # 处理data URI
                    image_data = image_data.split(',', 1)[1]
                image_data = base64.b64decode(image_data)
            
            # 存储图片数据
            key = f"img:{image_id}"
            self.set(key, image_data, expire)
            
            # 存储元数据（如果有）
            if metadata:
                meta_key = f"img_meta:{image_id}"
                self.set(meta_key, metadata, expire)
            
            return True
        except Exception as e:
            print(f"图片保存失败: {e}")
            return False
    
    def get_image(self, image_id: str, with_metadata: bool = False) -> Union[bytes, Dict, None]:
        """
        获取图片数据
        
        参数:
            image_id: 图片ID
            with_metadata: 是否同时返回元数据
            
        返回:
            图片数据（二进制）或包含图片和元数据的字典
        """
        key = f"img:{image_id}"
        image_data = self.get(key)
        
        if image_data is None:
            return None
        
        if with_metadata:
            meta_key = f"img_meta:{image_id}"
            metadata = self.get(meta_key, {})
            return {
                "image": image_data,
                "metadata": metadata
            }
        
        return image_data

    def get_image_cv2(self, image_id: str, with_metadata: bool = False) ->cv2.Mat:
        """
        获取图片数据

        参数:
            image_id: 图片ID
            with_metadata: 是否同时返回元数据

        返回:
            cv2格式图片
        """
        key = f"img:{image_id}"
        image_data = self.get(key)

        if image_data is None:
            return None

        # 将字节数据转换为NumPy数组
        nparr = np.frombuffer(image_data, np.uint8)

        # 使用OpenCV解码图像
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img

    def save_image_cv2(self, image_id: str, image_data: cv2.Mat,
                  metadata: Dict = None, expire: int = None) -> bool:
        """
        保存图片到缓存

        参数:
            image_id: 图片ID
            image_data: 图片数据（cv2.mat）
            metadata: 图片元数据
            expire: 过期时间（秒）

        返回:
            bool: 是否成功
        """
        try:
            # 将cv2.mat转换为字节数据
            _, img_encoded = cv2.imencode('.jpg', image_data)
            image_data = img_encoded.tobytes()

            # 存储图片数据
            key = f"img:{image_id}"
            self.set(key, image_data, expire)

            # 存储元数据（如果有）
            if metadata:
                meta_key = f"img_meta:{image_id}"
                self.set(meta_key, metadata, expire)

            return True
        except Exception as e:
            print(f"图片保存失败: {e}")
            return False


    def save_json(self, data_id: str, data: Dict, expire: int = None) -> bool:
        """
        保存JSON数据到缓存
        
        参数:
            data_id: 数据ID
            data: JSON可序列化的数据
            expire: 过期时间（秒）
            
        返回:
            bool: 是否成功
        """
        key = f"json:{data_id}"
        return self.set(key, data, expire)
    
    def get_json(self, data_id: str) -> Optional[Dict]:
        """
        获取JSON数据
        
        参数:
            data_id: 数据ID
            
        返回:
            JSON数据或None
        """
        key = f"json:{data_id}"
        return self.get(key)
    
    def update_json(self, data_id: str, update_data: Dict, expire: int = None) -> bool:
        """
        更新JSON数据
        
        参数:
            data_id: 数据ID
            update_data: 要更新的数据
            expire: 过期时间（秒）
            
        返回:
            bool: 是否成功
        """
        key = f"json:{data_id}"
        current_data = self.get(key)
        
        if current_data is None:
            return self.save_json(data_id, update_data, expire)
        
        if isinstance(current_data, dict):
            current_data.update(update_data)
            return self.set(key, current_data, expire)
        
        return False
    
    def list_keys(self, prefix: str = "") -> List[str]:
        """
        列出所有匹配前缀的键
        
        参数:
            prefix: 键前缀
            
        返回:
            匹配的键列表
        """
        return [key for key in self.cache if isinstance(key, str) and key.startswith(prefix)]
    
    def clear(self) -> bool:
        """
        清空缓存
        
        返回:
            bool: 是否成功
        """
        try:
            self.cache.clear()
            return True
        except Exception as e:
            print(f"缓存清空失败: {e}")
            return False
    
    def cleanup(self, days: int = None) -> int:
        """
        手动清理过期数据
        
        参数:
            days: 清理多少天前的数据，默认使用全局设置
            
        返回:
            int: 清理的项目数量
        """
        if days is None:
            expire_time = self.expire_seconds
        else:
            expire_time = days * 24 * 60 * 60
            
        # 获取当前时间戳
        current_time = time.time()
        count = 0
        
        # 遍历所有缓存项
        for key in list(self.cache):
            try:
                # 获取项目的过期时间
                expire = self.cache.expire(key)
                if expire is not None and current_time > expire:
                    self.cache.delete(key)
                    count += 1
            except Exception as e:
                print(f"清理项目失败 {key}: {e}")
                
        return count
    
    def _auto_cleanup(self) -> None:
        """
        自动清理线程，每天运行一次
        """
        while True:
            try:
                # 执行清理
                cleaned = self.cleanup()
                print(f"自动清理完成，删除了 {cleaned} 个过期项目")
                
                # 等待24小时
                time.sleep(24 * 60 * 60)
            except Exception as e:
                print(f"自动清理失败: {e}")
                # 如果出错，等待1小时后重试
                time.sleep(60 * 60)
    
    def close(self) -> None:
        """
        关闭缓存
        """
        self.cache.close()

# 创建默认缓存实例
default_cache = CacheSystem()

# 导出便捷函数
def get_cache() -> CacheSystem:
    """获取默认缓存实例"""
    return default_cache