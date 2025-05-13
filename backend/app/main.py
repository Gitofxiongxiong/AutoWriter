# app/main.py
import uvicorn # ASGI 服务器
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles # 用于提供静态文件服务
# 1. 导入 CORSMiddleware
from fastapi.middleware.cors import CORSMiddleware
from app.api import img_proc as upload_router # 正确导入img_proc模块
import os # 用于检查目录

# --- 创建 FastAPI 应用实例 ---
app = FastAPI(
    title="AutoWriter 后端服务",
    description="提供 AutoWriter 应用所需的后端 API 接口",
    version="0.1.0"
)

# --- 配置 CORS ---
# 2. 定义允许的来源列表
#    *   对于开发环境，通常是你的前端开发服务器地址，例如 Vue CLI 默认的 http://localhost:8080
#        或者 Vite 默认的 http://localhost:5173 或 http://127.0.0.1:5173
#    *   对于生产环境，应该是你的前端部署后的正式域名，例如 https://your-frontend.com
#    *   使用 ["*"] 表示允许所有来源，但这在生产环境中通常不安全，除非是完全公开的 API。
#        !!! 如果你的前端需要发送 cookies (credentials)，则不能使用 ["*"] !!!

origins = [
    "http://localhost",         # 允许本地主机（无端口）
    "http://localhost:8080",    # 假设你的前端开发服务器运行在 8080 端口
    "http://localhost:5173",    # Vite 默认端口之一
    "http://127.0.0.1:8080",    # 另一种本地访问方式
    "http://127.0.0.1:5173",    # 另一种本地访问方式
    # "https://your-production-frontend.com", # 部署后添加你的生产环境前端域名
]

# 3. 添加 CORS 中间件到应用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源,  # 设置允许的 origins 来源
    allow_credentials=True, # 指示跨域请求支持 cookies。如果设为 True，allow_origins 不能设为 ["*"]
    allow_methods=["*"],    # 允许所有方法 (GET, POST, PUT, DELETE 等) 或指定 ["GET", "POST"]
    allow_headers=["*"],    # 允许所有请求头或指定列表，例如 ["Content-Type", "Authorization"]
)

# --- 挂载 API 路由 ---
# 将 upload.py 中定义的路由挂载到 /api 前缀下
app.include_router(upload_router.router, prefix="/api", tags=["图片上传"])

# --- 挂载静态文件目录 (可选，但推荐) ---
# 这样可以通过 URL 访问 static 目录下的文件，例如 http://localhost:8079/static/图片名.jpg
# 注意: 'directory' 参数是相对于运行 main.py 的位置，确保路径正确
static_dir_path = "app/static"
if not os.path.exists(static_dir_path):
    print(f"警告: 静态文件目录 '{static_dir_path}' 不存在，将尝试创建。")
    try:
        os.makedirs(static_dir_path)
    except OSError as e:
         print(f"警告: 创建静态文件目录 '{static_dir_path}' 失败: {e}。静态文件服务可能无法正常工作。")

try:
    app.mount("/static", StaticFiles(directory=static_dir_path), name="static")
    print(f"静态文件目录 '{static_dir_path}' 已成功挂载到 /static 路径。")
except Exception as e:
    print(f"警告: 挂载静态文件目录 '{static_dir_path}' 失败: {e}。")


# --- 根路径 (可选) ---
@app.get("/", tags=["根路径"])
async def read_root():
    """访问根路径返回欢迎信息"""
    return {"message": "欢迎访问 AutoWriter 后端 API！"}


# --- 启动服务器 (用于直接运行 main.py) ---
if __name__ == "__main__":
    print("启动 AutoWriter 后端服务器...")
    print("访问 http://localhost:8079/docs 查看 API 文档")
    # 使用 uvicorn 启动 ASGI 应用
    # host="0.0.0.0" 表示监听所有可用网络接口，允许局域网访问
    # reload=True 表示开发模式，代码更改时自动重启 (生产环境应移除)
    uvicorn.run(
        "app.main:app",         # 指定应用实例位置: "文件名:FastAPI实例名"
        host="0.0.0.0",
        port=8079,          # 监听端口
        reload=True,        # 开发时启用自动重载
        log_level="info"    # 日志级别
    )