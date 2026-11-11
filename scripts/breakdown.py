#!/usr/bin/env python3
"""口播视频拆解：校验视频 -> 抽 16k 音频 -> 每 N 秒抽一帧 -> 本地转写。

用法（先跑过 scripts/setup.sh 一次装好环境）：
    python scripts/breakdown.py <视频文件> [--out work/<名字>] [--model small|base]

输出到工作目录：
    audio-16k.wav      16k 单声道音频
    frame-1.jpg ...    每 10 秒一帧（含第 0 秒）
    transcript.json    带时间戳的分段转写
    meta.json          视频信息（时长/分辨率/帧率/帧列表）

转写用本地 faster-whisper，不联网、不花钱。模型优先用项目内
models/faster-whisper-small（setup.sh 下载），没有就用 faster-whisper
自带的名字下载。音频以 numpy 数组喂模型（不要用文件路径直传）。
"""

import argparse
import json
import os
import subprocess
import sys
import wave

# 代理环境变量会干扰本地模型加载，先去掉；本地有模型时强制离线。
for _k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
           "all_proxy", "ALL_PROXY"):
    os.environ.pop(_k, None)


def run(cmd, err_msg):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"失败：{err_msg}\n命令：{' '.join(cmd)}\n{r.stderr.strip()[-500:]}",
              file=sys.stderr)
        sys.exit(3)
    return r


def probe(video):
    """ffprobe 校验视频可完整解码，返回基本信息。"""
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,r_frame_rate",
             "-show_entries", "format=duration",
             "-of", "json", video], "ffprobe 读取视频失败")
    d = json.loads(r.stdout)
    fmt = d.get("format", {})
    streams = d.get("streams", [])
    if not streams:
        print("失败：视频里没有视频流", file=sys.stderr)
        sys.exit(2)
    s = streams[0]
    num, den = s.get("r_frame_rate", "30/1").split("/")
    fps = round(int(num) / int(den), 2) if int(den) else 30
    has_audio = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0", video],
        capture_output=True, text=True).stdout.strip() != ""
    return {
        "duration": round(float(fmt.get("duration", 0)), 2),
        "width": s.get("width"),
        "height": s.get("height"),
        "fps": fps,
        "has_audio": has_audio,
    }


def resolve_model(name, model_dir_arg, project_root):
    """找本地模型目录；找不到就返回模型名，让 faster-whisper 自行下载。"""
    candidates = []
    if model_dir_arg:
        candidates.append(model_dir_arg)
    candidates.append(os.path.join(project_root, "models",
                                   f"faster-whisper-{name}"))
    for c in candidates:
        if c and os.path.isdir(c) and os.listdir(c):
            return c, True
    return name, False


def main():
    ap = argparse.ArgumentParser(description="口播视频拆解：抽音频/抽帧/本地转写")
    ap.add_argument("video", help="口播参考视频文件")
    ap.add_argument("--out", default=None, help="工作目录（默认 work/<视频名>）")
    ap.add_argument("--model", default="small", choices=["small", "base"],
                    help="转写模型（默认 small；听不清时用 base 复核）")
    ap.add_argument("--model-dir", default=None, help="本地模型目录")
    ap.add_argument("--frames-every", default=10, type=int,
                    help="抽帧间隔秒数（默认 10）")
    args = ap.parse_args()

    video = os.path.abspath(args.video)
    if not os.path.isfile(video):
        print(f"失败：找不到视频文件 {video}", file=sys.stderr)
        sys.exit(2)
    stem = os.path.splitext(os.path.basename(video))[0]
    out = os.path.abspath(args.out or os.path.join("work", stem))
    os.makedirs(out, exist_ok=True)
    project_root = os.path.abspath(os.path.join(
        os.path.dirname(__file__), ".."))

    info = probe(video)
    if not info["has_audio"]:
        print("失败：视频没有音轨，无法提取台词", file=sys.stderr)
        sys.exit(2)
    print(f"视频：{info['width']}x{info['height']} {info['fps']}fps "
          f"{info['duration']}s")

    wav = os.path.join(out, "audio-16k.wav")
    run(["ffmpeg", "-y", "-v", "error", "-i", video,
         "-ar", "16000", "-ac", "1", "-vn", wav], "抽音频失败")

    run(["ffmpeg", "-y", "-v", "error", "-i", video,
         "-vf", f"fps=1/{args.frames_every}",
         os.path.join(out, "frame-%d.jpg")], "抽帧失败")
    frames = sorted(f for f in os.listdir(out)
                    if f.startswith("frame-") and f.endswith(".jpg"))

    model_path, local = resolve_model(args.model, args.model_dir,
                                     project_root)
    if local:
        os.environ["HF_HUB_OFFLINE"] = "1"
    print(f"模型：{model_path}（{'本地' if local else '下载'}）")

    import numpy as np
    from faster_whisper import WhisperModel
    with wave.open(wav, "rb") as w:
        data = w.readframes(w.getnframes())
    audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    model = WhisperModel(model_path, device="cpu", compute_type="int8",
                         local_files_only=local)
    segments, meta = model.transcribe(audio, language="zh", vad_filter=True)
    out_segments = []
    for s in segments:
        out_segments.append({"start": round(s.start, 2),
                             "end": round(s.end, 2),
                             "text": s.text.strip()})
        print(f"[{s.start:.2f}-{s.end:.2f}] {s.text.strip()}")
    with open(os.path.join(out, "transcript.json"), "w",
              encoding="utf-8") as f:
        json.dump(out_segments, f, ensure_ascii=False, indent=2)
    with open(os.path.join(out, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({**info, "frames": frames,
                   "transcript": "transcript.json",
                   "audio": "audio-16k.wav"},
                  f, ensure_ascii=False, indent=2)
    print(f"完成：{out}（{len(out_segments)} 段台词，{len(frames)} 帧）")
    print(f"语言 {meta.language}，音频时长 {meta.duration:.1f}s")


if __name__ == "__main__":
    main()
