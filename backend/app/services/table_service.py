# app/services/table_service.py
import uuid
import cv2
from fastapi import UploadFile, HTTPException, status
from typing import Dict, Any
import json
from app.core.table_detect import TableDetect
from app.core.sheet_model.single_table import SingleTable
from app.core.cache import get_cache
from app.schemas.image_index import ImageIndex
from app.core.handword_gen.hw_converter import gen_handwriter_image
class TableService:
    """
    处理表格图片相关的业务逻辑，包括表格识别、图像校正等
    """
    
    async def detect_table_image(self, file: UploadFile) -> Dict[str, Any]:
        """
        处理表格图片，进行表格识别和校正
        
        Args:
            file: 上传的图片文件
            
        Returns:
            Dict: 包含校正后的图片URL和表格数据的字典
            
        Raises:
            HTTPException: 如果处理过程中发生错误
        """
        try:
            # 1. 基础验证：检查文件类型是否为图片
            if not file.content_type or not file.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="文件类型无效，只允许上传图片。",
                    )   

            cache = get_cache()
            img_index = ImageIndex()
            img_index.original_image_name = file.filename
            
            #保存原始图片
            img_index.original_image_key = uuid.uuid4().hex
            content = await file.read()
            cache = get_cache()
            if not cache.save_image(img_index.original_image_key, content):
                raise Exception("保存图片到缓存失败")

            #识别表格
            detector = TableDetect(img_index.original_image_key)
            sheet_type = await detector.get_sheet_type()
            if sheet_type == "singlesheet":
                table_info = await detector.get_table_info()
                 # 使用 SingleTable 处理图片
                single_table = SingleTable(img_index.original_image_key, table_info)
                # 获取校正后的图片
                corrected_image = single_table.get_corrected_image()
                # 保存校正后的图片到缓存
                img_index.corrected_image_key = uuid.uuid4().hex
                cache.save_image_cv2(img_index.corrected_image_key, corrected_image)

                # 获取绘制表格的图片
                drawed_image = single_table.get_drawed_image()
                # 保存绘制表格的图片到缓存
                img_index.drawed_image_key = uuid.uuid4().hex
                cache.save_image_cv2(img_index.drawed_image_key, drawed_image)

                # 获取表格数据
                web_tdtr_data = single_table.get_web_tdtr_data()
                # 保存 web_tdtr_data 到缓存
                img_index.web_tdtr_data_key = uuid.uuid4().hex
                cache.save_json(img_index.web_tdtr_data_key, web_tdtr_data)

                # 获取校正后的表格信息
                corrected_table_info = single_table.get_corrected_table_info()
                # 保存 corrected_table_info 到缓存  
                img_index.corrected_table_json_key = uuid.uuid4().hex
                cache.save_json(img_index.corrected_table_json_key, corrected_table_info)

                # 保存img_index到缓存
                img_index_key = uuid.uuid4().hex
                cache.save_json(img_index_key, img_index.model_dump())

                # 返回结果
                return {
                    "success": True,
                    "img_index_key": img_index_key,
                    "sheet_type": sheet_type,
                    "corrected_image_id": img_index.corrected_image_key,
                    "drawed_image_id": img_index.drawed_image_key,
                    "original_image_id": img_index.original_image_key,
                    "web_tdtr_data": web_tdtr_data,
                    "corrected_table_info": corrected_table_info
                }
            else:
                
                # 保存img_index到缓存
                img_index_key = uuid.uuid4().hex
                cache.save_json(img_index_key, img_index.model_dump())
                # 目前只支持单表格处理
                return {
                    "success": False,
                    "sheet_type": sheet_type,
                    "message": "目前只支持单表格处理",
                    "original_image_id": img_index.original_image_key
                }

        except Exception as e:
            # 记录异常信息
            error_message = str(e)
            print(f"识别图片表格时发生错误: {error_message}")
            
            # 抛出异常，由API层处理
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"处理图片失败: {error_message}"
            )

    async def gen_hw_image(self, table_data: Dict[str, Any], img_index_key: str) -> str:
        """
        生成手写字图片
        
        Args:
            table_data: 填写好的表格数据，格式参考 table-data-filled.json
            img_index_key: 图片索引的键值
            
        Returns:
            str: 生成的手写字图片键值
            
        Raises:
            HTTPException: 如果处理过程中发生错误
        """
        try:
            cache = get_cache()
            print(img_index_key)
            print("gen_hw_image")
            print(get_cache().list_keys())
            # 获取图片索引信息
            img_index_data = cache.get_json(img_index_key)
            if not img_index_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="找不到图片索引信息"
                )
            
            img_index = ImageIndex(**img_index_data)
            
            print("img_index_key: ",img_index)
            # 检查必要的键值是否存在
            if not img_index.corrected_image_key or not img_index.corrected_table_json_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="缺少校正后的图片或表格信息"
                )
            print("键值存在")
            # 获取校正后的图片
            corrected_image = cache.get_image_cv2(img_index.corrected_image_key)
            if corrected_image is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="找不到校正后的图片"
                )
            
            # 获取校正后的表格信息
            corrected_table_info = cache.get_json(img_index.corrected_table_json_key)
            if not corrected_table_info:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="找不到校正后的表格信息"
                )
            print("校正表格信息存在")
            # 获取表格单元格信息和文字信息
            tr_tables_info = corrected_table_info['data']['prism_tablesInfo'][0]['cellInfos']
            tr_word_info = corrected_table_info['data']['prism_wordsInfo']
            
            # 检查输入的表格数据
            if "tdtr_cells" not in table_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="无效的表格数据格式，缺少 tdtr_cells 字段"
                )
            print("输入的表格数据格式正确")
            input_table_info = table_data["tdtr_cells"]
            
            # 调用 gen_handwriter_image 生成手写字图片
            
            hw_image = gen_handwriter_image(tr_tables_info, tr_word_info, input_table_info, corrected_image)
            print("生成手写字图片成功")
            # 保存生成的手写字图片到缓存
            img_index.handwriting_image_key = uuid.uuid4().hex
            cache.save_image_cv2(img_index.handwriting_image_key, hw_image)
            cache.update_json(img_index.web_tdtr_data_key,{"tdtr_cells":input_table_info})

            # 更新图片索引
            cache.save_json(img_index_key, img_index.model_dump())
            
            return {
                "success": True,
                "img_index_key": img_index_key,
                "handwriting_image_id": img_index.handwriting_image_key
            }

            
        except HTTPException as http_exc:
            # 重新抛出 HTTP 异常
            raise http_exc
        except Exception as e:
            # 记录异常信息
            error_message = str(e)
            print(f"生成手写字图片时发生错误: {error_message}")
            
            # 抛出异常，由API层处理
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"生成手写字图片失败: {error_message}"
            )



# 依赖注入函数
def get_table_service() -> TableService:
    """依赖项工厂，返回 TableService 的实例"""
    return TableService()
