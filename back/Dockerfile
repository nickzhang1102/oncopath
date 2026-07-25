FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（PostgreSQL + libffi for cryptography + libGL for OpenCV + gosu + 中文字体）
# 注: fonts-wqy-zenhei (~5MB) 替代 fonts-noto-cjk (~120MB)，Chromium 渲染中文仅需一套 CJK 字体
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    pkg-config \
    libffi-dev \
    libgl1 \
    libglib2.0-0 \
    gosu \
    fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# 复制依赖文件
COPY requirements.txt .

# Keep the package installer above known-vulnerable versions in the runtime image.
RUN python -m pip install --no-cache-dir --upgrade "pip>=26.1.2"

# 安装Python依赖
# 禁用 oneDNN 以避免 PaddlePaddle 3.x 在 CPU 环境下的兼容性问题 (PIR 转换错误)
ENV FLAGS_use_onednn=0
# 设置 PaddleX/PaddleOCR 模型下载目录到 app 目录下，确保权限可控
ENV PADDLE_PDX_MODEL_DIR=/app/.paddlex
ENV PADDLE_OCR_MODEL_DIR=/app/.paddleocr
# 解决 PaddleOCR 3.x 可能出现的系统字符编码问题
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
# HuggingFace 镜像源（国内环境加速模型下载）
ENV HF_ENDPOINT=https://hf-mirror.com
ENV PADDLE_PDX_HUGGING_FACE_ENDPOINT=https://hf-mirror.com
# PaddleX 模型源优先级：bos(国内CDN) > modelscope > huggingface
ENV PADDLE_PDX_MODEL_SOURCE=bos

# 先安装 PaddlePaddle CPU 版（必须从官方源安装，PyPI 默认是 GPU 版）
RUN pip install --no-cache-dir --timeout 600 paddlepaddle==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/

# 先安装 PyTorch CPU 版（必须从官方源安装，PyPI 默认是 GPU 版，会拉 nvidia CUDA 包）
RUN pip install --no-cache-dir --timeout 600 torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu

# 安装 PaddleX OCR 额外依赖（表格识别 TableRecognitionPipelineV2 所需）
# 注意: paddlex[ocr] 会拉 opencv-contrib-python，后续 requirements.txt 中 opencv-python-headless 会覆盖
RUN pip install --no-cache-dir --timeout 600 "paddlex[ocr]" -i https://pypi.tuna.tsinghua.edu.cn/simple || \
    pip install --no-cache-dir --timeout 600 "paddlex[ocr]"

# 再安装其余依赖（跳过 paddlepaddle 和 torch 避免覆盖为 GPU 版）
RUN grep -v -E "^(paddlepaddle|torch)==" requirements.txt > /tmp/req_no_gpu.txt && \
    pip install --no-cache-dir --timeout 600 -i https://pypi.tuna.tsinghua.edu.cn/simple -r /tmp/req_no_gpu.txt

# 安装 Playwright Chromium 浏览器（含系统依赖，用于 PDF 导出）
# 浏览器归档由 Playwright 官方安装器按当前 Python 包版本解析和安装。
# 注意: 不使用 playwright install-deps（会回退 Ubuntu 20.04 包名，Debian Trixie 不兼容），
# 改为手动安装 Chromium 运行所需的系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.cache/ms-playwright
RUN timeout 600 python -m playwright install chromium

# 预下载 PaddleOCR 基础模型（避免运行时首次请求下载失败）
RUN timeout 600 python -c "from paddleocr import PaddleOCR; ocr = PaddleOCR(lang='ch', device='cpu', use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False); print('PaddleOCR base models downloaded')" || echo "WARNING: PaddleOCR base model download failed, will retry at runtime"

# 预下载表格识别模型（TableRecognitionPipelineV2 所需的 6 个子模型）
RUN timeout 600 python -c "from paddleocr import TableRecognitionPipelineV2; p = TableRecognitionPipelineV2(device='cpu'); print('TableRecognition models downloaded')" || echo "WARNING: TableRecognition model download failed, will retry at runtime"

# 复制应用代码
COPY . .

# 创建缓存目录和存储目录并设置权限
RUN mkdir -p /app/.cache /app/.paddlex /app/.paddleocr /app/.cache/ms-playwright /app/storage/images /app/storage/thumbnails /app/storage/documents /app/storage/pathology \
    && chown -R appuser:appuser /app \
    && sed -i 's/\r$//' /app/docker-entrypoint.sh \
    && chmod +x /app/docker-entrypoint.sh

# 容器以 root 启动，entrypoint 中修复权限后通过 gosu 切换到 appuser
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
