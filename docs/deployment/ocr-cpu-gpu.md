# PaddleOCR CPU / NVIDIA GPU 部署指南

OncoPath 提供 CPU 默认环境和 NVIDIA GPU 覆盖环境。GPU 使用 `docker-compose.yml` 加 `docker-compose.gpu.yml` 两个文件启用；后者是独立维护的覆盖文件，不是可单独启动的完整 Compose。两者使用相同的应用代码、数据库和存储卷，只在 PaddlePaddle wheel、容器 GPU 权限和推理设备上不同。

> 本项目当前不支持云端 OCR、AMD GPU、Apple Silicon GPU、多 GPU 调度或运行时热切换。GPU 环境固定使用 PaddlePaddle 3.2.0 的 CUDA 12.6 wheel，并使用容器内第一张可见 NVIDIA GPU（`gpu:0`）。

## 先选择部署环境

| 环境 | 适合场景 | 主机要求 | 启动文件 |
|------|----------|----------|----------|
| CPU（默认） | 无 NVIDIA GPU、低频 OCR、优先部署简单 | x86_64 CPU，建议 4 核、8 GB 内存 | `docker-compose.yml` |
| NVIDIA GPU | OCR 频繁、报告图片较大、需要降低本地识别耗时 | 支持 CUDA 12.6 的 NVIDIA 驱动、NVIDIA Container Toolkit；建议 8 GB 或以上显存 | `docker-compose.yml` + `docker-compose.gpu.yml` |

GPU 只加速 PaddleOCR 的基础文本识别和表格识别。本项目后续的 OCR LLM 解析仍调用 `OCR_LLM_API_BASE`，其延迟和费用不会因本地 GPU 改变。识别出的文本可能会发送给该 LLM 服务，部署者仍需评估相应的医疗数据与隐私边界。

> PostgreSQL 的容器端口固定为 `5432`，GPU 不会改变它。主 Compose 默认把宿主机调试端口映射为 `127.0.0.1:15432`；如该端口也被占用，在 `.env` 中设置其他 `DB_HOST_PORT`，或删除 PostgreSQL 的 `ports` 映射。backend 始终使用 `postgres:5432`。

## 共同准备

两种环境都先完成以下步骤：

```bash
git clone <repository-url>
cd oncopath
cp .env.example .env
```

编辑 `.env`，至少配置数据库、Redis、应用密钥、PHI 加密密钥和 OCR LLM：

```dotenv
DB_PASSWORD=<强密码>
REDIS_PASSWORD=<强密码>
SECRET_KEY=<至少 32 字符的随机值>
ENCRYPTION_KEY=<Fernet 密钥>
ALLOW_UNENCRYPTED_PHI=false

OCR_LLM_API_KEY=<你的 API Key>
OCR_LLM_API_BASE=<OpenAI 兼容接口地址>
OCR_LLM_MODEL_NAME=<模型名>
```

Docker 部署不要在 `.env` 中自行切换 `OCR_PADDLE_DEVICE`。默认 Compose 固定为 `cpu`，GPU 覆盖文件固定为 `gpu:0`，从而保证运行时设备与镜像中安装的 wheel 一致。

## CPU 环境

### 构建和启动

CPU 是默认环境，只使用主 Compose 文件：

```bash
docker compose --env-file .env -p oncopath \
  -f docker-compose.yml build backend

docker compose --env-file .env -p oncopath \
  -f docker-compose.yml up -d
```

也可以使用部署脚本；脚本会拉取 `main`、无缓存重建并重启全部服务：

```bash
bash scripts/deploy.sh production cpu
```

### 验证 CPU wheel 与设备

```bash
docker compose --env-file .env -p oncopath \
  -f docker-compose.yml exec backend python - <<'PY'
import paddle
from app.services.ocr.ocr_config import ocr_config

print("PaddlePaddle:", paddle.__version__)
print("compiled_with_cuda:", paddle.device.is_compiled_with_cuda())
print("OCR device:", ocr_config.paddle_device)
paddle.set_device(ocr_config.paddle_device)
print("active device:", paddle.device.get_device())
PY
```

预期结果：

- `PaddlePaddle` 为 `3.2.0`；
- `compiled_with_cuda` 为 `False`；
- `OCR device` 和 `active device` 均为 `cpu`。

首次上传脱敏测试报告后，后端日志应包含：

```text
[PaddleOCR] 基础识别模型初始化完成，device=cpu
[TablePipeline] TableRecognitionPipelineV2 初始化完成，device=cpu
```

## NVIDIA GPU 环境

### 1. 检查主机 GPU 与驱动

生产目标是 Linux x86_64。先在宿主机执行：

```bash
nvidia-smi
```

命令必须能看到目标 GPU，并且显示的驱动支持 CUDA 12.6。这里检查的是驱动能力；宿主机不需要另外安装 PaddlePaddle。

### 2. 安装并验证 NVIDIA Container Toolkit

按照 NVIDIA 官方文档为当前发行版安装 NVIDIA Container Toolkit，配置 Docker runtime 后重启 Docker。随后验证容器能访问 GPU：

```bash
docker run --rm --gpus all ubuntu nvidia-smi
```

如果这一步失败，不要继续构建 OncoPath GPU 环境；先修复 Docker 的 GPU runtime。

### 3. 检查最终 Compose 配置

GPU 部署必须始终同时传入两个 Compose 文件：

```bash
docker compose --env-file .env -p oncopath \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml config
```

合并结果中的 backend 应同时满足：

- 构建参数 `OCR_PADDLE_DEVICE: gpu:0`；
- 容器环境变量 `OCR_PADDLE_DEVICE: gpu:0`；
- `deploy.resources.reservations.devices` 包含 `driver: nvidia` 和 `capabilities: [gpu]`。
- PostgreSQL 的宿主机调试映射使用 `DB_HOST_PORT`（默认 `15432`），不会占用宿主机 `5432`。

### 4. 构建和启动

```bash
docker compose --env-file .env -p oncopath \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml build backend

docker compose --env-file .env -p oncopath \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml up -d
```

首次从 CPU 切换到 GPU，或修改过构建参数时，建议强制重建 backend，排除旧 CPU layer：

```bash
docker compose --env-file .env -p oncopath \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml build --no-cache backend

docker compose --env-file .env -p oncopath \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml up -d --force-recreate backend
```

部署脚本等价入口：

```bash
bash scripts/deploy.sh production gpu
```

### 5. 验证 GPU wheel、容器权限和计算设备

```bash
docker compose --env-file .env -p oncopath \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml exec backend python - <<'PY'
import paddle
from app.services.ocr.ocr_config import ocr_config

print("PaddlePaddle:", paddle.__version__)
print("compiled_with_cuda:", paddle.device.is_compiled_with_cuda())
print("visible GPUs:", paddle.device.cuda.device_count())
print("OCR device:", ocr_config.paddle_device)

if not paddle.device.is_compiled_with_cuda():
    raise SystemExit("错误：当前容器安装的不是 PaddlePaddle GPU wheel")
if paddle.device.cuda.device_count() < 1:
    raise SystemExit("错误：容器没有可见的 NVIDIA GPU")

paddle.set_device(ocr_config.paddle_device)
result = paddle.ones([2, 2]) @ paddle.ones([2, 2])
print("active device:", paddle.device.get_device())
print("tensor place:", result.place)
PY
```

预期结果：

- `PaddlePaddle` 为 `3.2.0`；
- `compiled_with_cuda` 为 `True`；
- `visible GPUs` 至少为 `1`；
- `OCR device` 与 `active device` 为 `gpu:0`；
- `tensor place` 显示 GPU 设备。

最后上传一张不含真实患者信息的测试报告。后端日志应包含：

```text
[PaddleOCR] 基础识别模型初始化完成，device=gpu:0
[TablePipeline] TableRecognitionPipelineV2 初始化完成，device=gpu:0
```

可在宿主机另一个终端运行 `watch -n 1 nvidia-smi`，确认首次 OCR 期间 backend 进程占用显存。PaddleOCR 使用延迟初始化，未执行 OCR 前看不到显存占用是正常现象。

## CPU 与 GPU 之间切换

切换不会迁移或删除 PostgreSQL、Redis、上传文件和模型卷，但必须重建并强制重建 backend。建议安排维护窗口；不要使用 `down -v`。

从 CPU 切换到 GPU：

```bash
docker compose --env-file .env -p oncopath \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml build --no-cache backend
docker compose --env-file .env -p oncopath \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml up -d --force-recreate backend
```

从 GPU 切回 CPU：

```bash
docker compose --env-file .env -p oncopath \
  -f docker-compose.yml build --no-cache backend
docker compose --env-file .env -p oncopath \
  -f docker-compose.yml up -d --force-recreate backend
```

切换后务必重新执行对应环境的设备验证命令。只修改容器环境变量或只执行 `restart` 不会替换已经安装的 PaddlePaddle wheel，因此不属于有效切换。

## 日常升级与运维

CPU 环境的所有命令只使用 `docker-compose.yml`。GPU 环境的 build、up、exec、logs、ps 和 down 都应同时携带两个 `-f` 参数，例如：

```bash
docker compose -p oncopath \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml logs -f backend
```

更新代码后，使用当前环境对应的文件集合重新构建。GPU 环境不要省略覆盖文件，否则会把 backend 重建成 CPU 版。

## 非 Docker 本地开发

默认 CPU 安装：

```bash
pip install paddlepaddle==3.2.0 \
  -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
export OCR_PADDLE_DEVICE=cpu
```

Linux x86_64 NVIDIA GPU（CUDA 12.6 wheel）：

```bash
pip uninstall -y paddlepaddle paddlepaddle-gpu
pip install paddlepaddle-gpu==3.2.0 \
  -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
export OCR_PADDLE_DEVICE=gpu:0
```

本地环境同样只能安装一个 PaddlePaddle variant。切换后使用前文 Python 检查确认实际设备。

## 故障排查

### 当前 PaddlePaddle 不包含 CUDA 支持

日志包含：

```text
OCR_PADDLE_DEVICE 配置为 GPU，但当前 PaddlePaddle 不包含 CUDA 支持
```

说明容器运行参数是 GPU，但镜像仍是 CPU wheel。确认构建和启动命令都带两个 Compose 文件，然后对 backend 执行 `build --no-cache` 与 `up --force-recreate`。

### Docker 找不到 NVIDIA runtime 或设备

常见报错包括 `could not select device driver`、`unknown runtime nvidia`、`no devices found`。先让以下命令成功：

```bash
docker run --rm --gpus all ubuntu nvidia-smi
```

失败通常表示 NVIDIA Container Toolkit 未安装、未配置给 Docker，或 Docker 服务尚未重启。

### 驱动或 CUDA 不兼容

如果 Paddle 导入或首次计算报 CUDA/driver 版本错误，升级宿主机 NVIDIA 驱动，使 `nvidia-smi` 显示支持 CUDA 12.6；不要在容器内安装另一套显卡驱动。

### GPU 显存不足

基础 OCR 与表格识别都会使用同一张 GPU，且当前 OCR 线程池最多允许两个任务并行。长图、PDF 或并发上传可能提高峰值显存。先用单张普通图片验证，停止并发上传，并通过 `nvidia-smi` 确认是否 OOM。首版不提供多 GPU 分流或自动退回 CPU。

### GPU 没有占用

先运行设备验证脚本，再实际上传测试报告。服务启动本身不会加载 PaddleOCR 模型；只有首个 OCR 请求才会延迟初始化。若日志仍显示 `device=cpu`，说明启动时漏掉了 GPU Compose 覆盖文件。

### 首次 OCR 很慢或模型下载失败

镜像构建会尝试预下载基础 OCR 和表格模型，但下载失败不会中断构建，运行时会重试。检查 backend 到 Paddle/Hugging Face 镜像源的网络、模型卷权限和磁盘空间：

```bash
docker compose -p oncopath -f docker-compose.yml \
  -f docker-compose.gpu.yml logs --tail=200 backend
docker compose -p oncopath -f docker-compose.yml \
  -f docker-compose.gpu.yml exec backend df -h
```

CPU 环境排查时去掉 `docker-compose.gpu.yml`。
