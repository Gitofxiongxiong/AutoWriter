# app/api/img_proc.py
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status
from typing import Dict, Any, List
from app.schemas.table_info_struct import HWTableDataRequest
from app.services.image_service import ImageService, get_image_service
from app.services.table_service import TableService, get_table_service
from fastapi.responses import FileResponse
import os
from app.core.cache import get_cache
import uuid
from fastapi.background import BackgroundTasks  # 将 BackgroundTask 改为 BackgroundTasks

# 创建一个 API 路由实例
router = APIRouter(prefix="/img_proc", tags=["图片处理"])

@router.post(
    "/detect_table_image",
    summary="处理表格图片",
    description="接收用户上传的表格图片，进行校正和表格识别",
    status_code=status.HTTP_200_OK
)
async def detect_table_image(
    file: UploadFile = File(..., description="要处理的表格图片文件"),
    table_service: TableService = Depends(get_table_service)
) -> Dict[str, Any]:
    """
    处理表格图片接口
    
    接收图片文件，进行表格识别和校正，返回校正后的图片和表格数据
    """
    try:
        # 调用服务层处理表格图片
        result = await table_service.detect_table_image(file)
        return result
    except HTTPException as http_exc:
        # 如果服务层抛出的是 HTTPException，直接重新抛出
        raise http_exc
    except Exception as e:
        # 捕获其他意外错误
        print(f"API 层捕获到未知错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发生意外错误: {e}",
        )

@router.post(
    "/uploadOrgImage",
    summary="上传原始图片",
    description="接收用户上传的图片文件，并保存到服务器的 static 目录。",
    status_code=status.HTTP_201_CREATED
)
async def upload_original_image(
    file: UploadFile = File(..., description="要上传的图片文件"),
    image_service: ImageService = Depends(get_image_service)
) -> Dict[str, Any]:
    """
    处理图片上传请求的 API 端点。
    """
    try:
        # 调用服务层的方法来保存图片
        saved_filename = await image_service.save_image(file)
        # 返回成功响应，包含保存后的文件名
        return {
            "code": 0,
            "message": "上传成功",
            "data": {
                "url": f"/static/{saved_filename}"
            }
        }
    except HTTPException as http_exc:
        # 如果服务层抛出的是 HTTPException，直接重新抛出
        raise http_exc
    except Exception as e:
        # 捕获其他意外错误
        print(f"API 层捕获到未知错误: {e}")
        return {
            "code": 500,
            "message": f"上传失败: {e}",
            "data": None
        }


@router.get(
    "/image/{image_id}",
    summary="获取图片",
    description="根据图片ID获取图片文件",
    response_class=FileResponse
)
async def get_image(
    image_id: str,
    background_tasks: BackgroundTasks  # 添加参数
):
    """
    获取图片接口
    
    根据图片ID返回图片文件
    """
    try:
        # 从缓存中获取图片
        cache = get_cache()
        image_data = cache.get_image(image_id)
        
        # 检查图片是否存在
        if image_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"图片不存在: {image_id}"
            )
        
        # 创建临时文件并写入图片数据
        temp_dir = os.path.join(os.path.dirname(__file__), "..", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # 生成临时文件路径
        file_extension = os.path.splitext(image_id)[1] if "." in image_id else ".jpg"
        temp_file_path = os.path.join(temp_dir, f"temp_{uuid.uuid4()}{file_extension}")
        
        # 写入图片数据到临时文件
        with open(temp_file_path, "wb") as f:
            f.write(image_data)
        
        # 返回临时文件
        # 修改返回语句，使用 background_tasks
        background_tasks.add_task(lambda: os.unlink(temp_file_path) if os.path.exists(temp_file_path) else None)
        return FileResponse(
            path=temp_file_path,
            filename=image_id
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"获取图片时发生错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取图片失败: {e}"
        )



@router.post(
    "/gen_hw_image",
    summary="生成手写字图片",
    description="根据填写好的表格数据生成手写字图片",
)
async def gen_hw_image(
    table_data: HWTableDataRequest,
    table_service: TableService = Depends(get_table_service)
)-> Dict[str, Any]:
    """
    生成手写字图片接口
    
    根据填写好的表格数据生成手写字图片ID
    """
    try:
        # 调用服务层生成手写字图片
        res = await table_service.gen_hw_image(
                table_data.model_dump(), 
                table_data.img_index_key
            )
        return res
        
    except HTTPException as http_exc:
        # 如果服务层抛出的是 HTTPException，直接重新抛出
        raise http_exc
    except Exception as e:
        # 捕获其他意外错误
        print(f"API 层捕获到未知错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成手写字图片失败: {e}",
        )
        