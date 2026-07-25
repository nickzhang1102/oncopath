"""启动脚本 - 解决Windows环境下OpenMP冲突"""
import os
# 必须在导入torch之前设置
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        reload_dirs=["D:\\dev\\medical\\medical2.0\\back"]
    )
