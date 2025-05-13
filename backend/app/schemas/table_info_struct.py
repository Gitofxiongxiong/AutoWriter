from pydantic import BaseModel
from typing import Dict, Any, List
# 定义请求体模型
class HWTableDataRequest(BaseModel):
    rows: int
    cols: int
    tdtr_cells: List[List[Dict[str, Any]]]
    img_index_key: str
