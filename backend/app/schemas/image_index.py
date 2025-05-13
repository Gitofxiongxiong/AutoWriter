from pydantic import BaseModel
from typing import Optional

class ImageIndex(BaseModel):
    """
    图片相关存储信息的索引类
    
    用于存储与图片处理相关的各种键值和信息
    """
    
    # 原始图片的名字
    original_image_name: str = ""  # 设置默认值为空字符串
    
    # 原始图片存储的键值
    original_image_key: str = ""   # 设置默认值为空字符串
    
    # 矫正后图片存储的键值
    corrected_image_key: Optional[str] = None
    
    # 表格识别数据json文件存储的键值
    corrected_table_json_key: Optional[str] = None
    
    # tdtr_json文件存储的键值
    web_tdtr_data_key: Optional[str] = None
    
    # 绘制上表格的图片存储键值
    drawed_image_key: Optional[str] = None
    
    # 手写字图片存储的键值
    handwriting_image_key: Optional[str] = None
    
    class Config:
        """Pydantic配置类"""
        schema_extra = {
            "example": {
                "original_image_name": "example.jpg",
                "original_image_key": "12345abcde.jpg",
                "corrected_image_key": "corrected_12345abcde.jpg",
                "corrected_table_json_key": "table_12345abcde",
                "web_tdtr_data_key": "web_tdtr_12345abcde",
                "drawed_image_key": "drawed_12345abcde.jpg",
                "handwriting_image_key": "handwriting_12345abcde.jpg"
            }
        }