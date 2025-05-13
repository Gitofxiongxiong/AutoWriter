# app/services/image_service.py
import os
import uuid # 用于生成唯一文件名
import aiofiles # 用于异步文件操作
from fastapi import UploadFile, HTTPException, status

# 定义静态文件存储目录 (相对于 backend 目录)
# 注意：这种相对路径在不同运行方式下可能需要调整，更健壮的方式是使用配置或绝对路径
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))

class ImageService:
    """
    处理图片相关的业务逻辑，例如保存图片。
    """
    async def save_image(self, file: UploadFile) -> str:
        """
        将上传的图片文件保存到 static 目录。

        Args:
            file: 上传的文件对象 (UploadFile).

        Returns:
            保存后的文件名 (str).

        Raises:
            HTTPException: 如果文件类型无效或保存失败。
            IOError: 如果文件写入时发生错误。
        """
        # 1. 基础验证：检查文件类型是否为图片
        if not file.content_type or not file.content_type.startswith("image/"):
            print(f"无效的文件类型: {file.content_type}") # 调试信息
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件类型无效，只允许上传图片。",
            )

        # 2. 确保 static 目录存在
        try:
            os.makedirs(STATIC_DIR, exist_ok=True)
        except OSError as e:
            print(f"创建目录失败: {STATIC_DIR}, 错误: {e}") # 调试信息
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"无法创建存储目录: {e}",
            )

        # 3. 生成唯一文件名，保留原始扩展名
        original_filename = file.filename if file.filename else "unknown"
        _, ext = os.path.splitext(original_filename)
        # 如果没有扩展名，尝试从 content_type 推断
        if not ext:
            content_type = file.content_type
            if content_type == "image/jpeg":
                ext = ".jpg"
            elif content_type == "image/png":
                ext = ".png"
            elif content_type == "image/gif":
                ext = ".gif"
            elif content_type == "image/webp":
                ext = ".webp"
            else:
                ext = "" # 无法确定则不加扩展名

        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(STATIC_DIR, unique_filename)

        print(f"准备保存图片到: {file_path}") # 调试信息

        # 4. 异步写入文件
        try:
            # 使用 aiofiles 进行异步写入，适合 FastAPI
            async with aiofiles.open(file_path, 'wb') as out_file:
                while content := await file.read(1024 * 1024):  # 每次读取 1MB
                    await out_file.write(content)
            print(f"图片保存成功: {unique_filename}") # 调试信息
            return unique_filename # 返回保存后的文件名
        except Exception as e:
            print(f"保存文件时出错: {e}") # 调试信息
            # 在实际应用中，这里应该记录更详细的错误日志
            # 可以选择删除可能已创建的不完整文件
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass # 删除失败也无能为力，记录日志
            # 抛出 IO 错误或自定义错误，让上层处理
            raise IOError(f"无法保存文件 {unique_filename}: {e}")


# --- 依赖注入函数 ---
# 这个简单的函数让 FastAPI 的 Depends 系统能够在需要时
# 创建 ImageService 的实例，注入到 API 路由函数中。
def get_image_service() -> ImageService:
    """依赖项工厂，返回 ImageService 的实例"""
    return ImageService()