import os
import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any, Literal
import base64
from pathlib import Path
from app.core.cache import get_cache
class TableDetect:
    """
    表格检测类，用于识别图片中的表格和文字，并判断sheet类型
    """
    
    def __init__(self, image_index: str):
        """
        初始化表格检测类
        
        Args:
            image_index: 图片路径
        """
        self.image_index = image_index
        self.result: Optional[Dict[str, Any]] = None
        self._processing = False
        self._processed = False
        self._processing_task = None
    
    async def process(self):
        """
        处理图片，调用阿里云API识别表格和文字
        """
        if self._processing or self._processed:
            return
        
        self._processing = True
        
        try:
            # # 测试模式，直接读取本地JSON文件
            # if self.image_path == "F:\\typewriter\\AutoWriter\\test_img.jpg":
            #     await self._mock_api_call()
            # else:
            #     await self._call_aliyun_api()
            await self._mock_api_call()
            self._processed = True
        except Exception as e:
            raise Exception(f"表格识别处理失败: {str(e)}")
        finally:
            self._processing = False
    
    async def _mock_api_call(self):
        """
        模拟API调用，用于测试
        """
        # 模拟API处理时间
        await asyncio.sleep(0.5)
        
        # 读取本地JSON文件
        json_path = "F:\\typewriter\\AutoWriter\\table.json"
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                self.result = json.load(f)
        except Exception as e:
            raise Exception(f"读取模拟数据失败: {str(e)}")
    
    async def _call_aliyun_api(self):
        """
        调用阿里云API识别表格和文字
        """
        # 这里是阿里云API调用的实现
        # 实际项目中需要替换为真实的API调用代码
        try:
            # 读取图片文件并转为base64
            
            image_content = get_cache(self.image_index) 
            
            image_base64 = base64.b64encode(image_content).decode('utf-8')
            
            # 阿里云API调用参数
            # 注意：这里需要替换为实际的API密钥和参数
            api_url = "https://ocr-api.aliyuncs.com/recognize/table"
            headers = {
                "Authorization": "YOUR_API_KEY",
                "Content-Type": "application/json"
            }
            payload = {
                "image": image_base64
            }
            
            # 异步调用API
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        self.result = await response.json()
                        
                    else:
                        error_text = await response.text()
                        raise Exception(f"API调用失败: {response.status}, {error_text}")
        except Exception as e:
            raise Exception(f"调用阿里云API失败: {str(e)}")
    
    async def ensure_processed(self):
        """
        确保图片已经处理完成
        """
        if not self._processed and not self._processing:
            self._processing_task = asyncio.create_task(self.process())
            await self._processing_task
        elif self._processing and self._processing_task:
            await self._processing_task
    
    async def get_sheet_type(self) -> Literal["singlesheet", "othersheet"]:
        """
        判断sheet类型
        
        Returns:
            sheet类型: "singlesheet" 或 "othersheet"
        """
        await self.ensure_processed()
        
        if not self.result:
            raise Exception("表格识别结果为空")
        
        try:
            # 判断是否只有一个表格，且tableId=0
            tables_info = self.result.get("data", {}).get("prism_tablesInfo", [])
            if len(tables_info) == 1 and tables_info[0].get("tableId", -1) == 0:
                return "singlesheet"
            else:
                return "othersheet"
        except Exception as e:
            raise Exception(f"判断sheet类型失败: {str(e)}")
    
    async def get_table_info(self) -> Dict[str, Any]:
        """
        获取表格和文字信息
        
        Returns:
            表格和文字信息
        """
        await self.ensure_processed()
        
        if not self.result:
            raise Exception("表格识别结果为空")
        
        return self.result


if __name__ == "__main__":
    async def test():
     # 测试接口，使用测试图片
        detector = TableDetect("F:\\typewriter\\AutoWriter\\test_img.jpg")
        # 处理图片
        await detector.process()
        # 获取sheet类型
        sheet_type = await detector.get_sheet_type()
        
        # 获取表格信息
        table_info = await detector.get_table_info()

        print(f"sheet类型: {sheet_type}")
        print(f"表格信息: {table_info}")

    asyncio.run(test())