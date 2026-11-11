#!/usr/bin/env bash
# 一键安装本项目所需的本地环境（只需跑一次，之后所有视频共用）。
# 装完：项目自带 .venv（含 faster-whisper）+ models/faster-whisper-small。
# 用法：在项目根目录跑  bash scripts/setup.sh
# 国内下载模型慢，可先 export HF_ENDPOINT=https://hf-mirror.com 再跑。
set -euo pipefail
cd "$(dirname "$0")/.."

command -v python3 >/dev/null || { echo "失败：没找到 python3，先装 Python 3.9+"; exit 1; }
if ! command -v ffmpeg >/dev/null; then
  echo "失败：没找到 ffmpeg。"
  echo "  macOS:   brew install ffmpeg"
  echo "  Windows: winget install Gyan.FFmpeg"
  echo "  Ubuntu:  sudo apt install ffmpeg"
  exit 1
fi

if [ ! -d .venv ]; then
  echo "创建虚拟环境 .venv ..."
  python3 -m venv .venv
fi
echo "安装 faster-whisper ..."
.venv/bin/pip install --quiet --upgrade pip faster-whisper numpy

if [ ! -d models/faster-whisper-small ] || [ -z "$(ls -A models/faster-whisper-small 2>/dev/null)" ]; then
  echo "下载转写模型 faster-whisper-small（约 500MB，一次下载之后不用再下）..."
  .venv/bin/python - <<'EOF'
from huggingface_hub import snapshot_download
snapshot_download("Systran/faster-whisper-small",
                  local_dir="models/faster-whisper-small")
EOF
else
  echo "模型已在 models/faster-whisper-small，跳过下载。"
fi

.venv/bin/python -c "import faster_whisper; print('faster-whisper 就绪')"
echo "安装完成。试跑：.venv/bin/python scripts/breakdown.py <你的视频>.mp4"
