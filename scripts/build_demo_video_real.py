"""Build the real-page competition demo with neural narration and subtitles."""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
from pathlib import Path

import edge_tts


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "submission_artifacts" / "video_real"
CAPTURES = BASE / "captures"
AUDIO = BASE / "audio"
CLIPS = BASE / "clips"
OUTPUT = ROOT / "submission_artifacts" / "云穗智擎_山东建筑大学_张衡_项目演示视频_实录版.mp4"
SRT = ROOT / "submission_artifacts" / "云穗智擎_山东建筑大学_张衡_项目演示视频_实录版.srt"


# The spoken version preserves every claim in the approved script, while replacing
# document-style run-on sentences with pauses that sound natural in a presentation.
SEGMENTS = [
    {
        "id": "01_problem",
        "duration": 25,
        "text": "县域农业一线，病虫害防控一直有四个老问题：发现滞后，数据分散，研判靠经验，植保资源也常常平均分配。农智云瞰以济宁市鱼台县为示范，把这些问题，转化成可度量、可追踪的数据问题。",
    },
    {
        "id": "02_data",
        "duration": 55,
        "text": "平台的数据底座，是县域农情数据湖。明细层覆盖二十四个月、六个乡镇、八十个地块和五类作物。传感器逐时数据一百四十万条，气象观测十万条，田间踏查六点六万条，测产实测一点四万条，合计一百五十九万条，并按月分区、按乡镇落盘。真实采集一定会有脏数据。因此，我们主动注入丢包、重复和故障读数，检验清洗能力。Spark 最终剔除重复四千七百二十七条，异常与关键缺失三千三百三十二条，保留一百五十八万条，有效率百分之九十九点四九。每一项，都可以核对。",
    },
    {
        "id": "03_spark",
        "duration": 60,
        "text": "离线分析以 Apache Spark 为主链路，不是一个可有可无的扩展。原始明细不进入业务库，业务库只消费 Spark 的分析结果。DWD 层负责去重、值域过滤、缺失处理和时间口径统一。DWS 层按乡镇日、地块日两级汇聚，再用窗口函数计算近十四天的历史病害压力。这样，模型看到的不再是一个孤立的观测点，而是连续变化的累积效应。最终形成五万八千四百行地块日特征宽表。ADS 层再通过 Spark SQL，产出风险排名、作物风险、七日趋势、产量预测、巡检优先级和农资调度六类结果。",
    },
    {
        "id": "04_risk",
        "duration": 50,
        "text": "风险评分综合空气湿度、降雨、土壤墒情、历史病害和积温，再结合不同作物的易感性。风险阈值也不是凭经验拍出来的。我们对五万八千四百条记录做分位数统计，把五十二分设为高风险，三十六分设为中风险，再用主汛期发生率校核。以八月三十一日为例，全县有十四个高风险地块、三十六个中风险地块，重点集中在水稻和番茄。系统不仅告诉我们哪里风险高，还会给出主导因子，并进一步换算无人机架次、农技人员和药剂需求。",
    },
    {
        "id": "05_system",
        "duration": 60,
        "text": "在线系统把分析结果，真正落到业务动作上。驾驶舱展示全县态势；风险地图按等级为地块着色，并给出主导因子；上传叶片图片后，识别服务返回病害名称、置信度、严重度、检测框和人工复核标记。预警可以一键转为巡检任务，现场处理结果再回写系统。农技助手优先检索 RAGFlow 知识库，同时引用当前风险数据；最后，一键生成农情日报。这里也要说明：PlantDoc 和 IP102 验证集的 mAP50 分别为零点六五和零点四一。它们只代表公开数据集成绩，不代表山东本地田间准确率。实际落地前，必须补充本地样本，并保留专家复核。",
    },
    {
        "id": "06_engineering",
        "duration": 25,
        "text": "为了让结果可以复核，而不是一次性跑数，项目还提供了与 Spark 同口径的 pandas 参考实现。比对脚本逐表、逐字段校验两条链路。造数使用固定随机种子，记录不足一百万条就直接失败退出。全系统支持 Docker 一键部署。",
    },
    {
        "id": "07_close",
        "duration": 15,
        "text": "从一百五十九万条明细，到 Spark 四层数仓，再到风险预警和资源调度。农智云瞰，让县域植保从被动上报，走向数据驱动的主动决策。",
    },
]


def ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def run(args: list[str]) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def media_duration(path: Path) -> float:
    result = subprocess.run(
        [ffmpeg(), "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
    if not match:
        raise RuntimeError(f"Cannot read duration: {path}")
    hour, minute, second = match.groups()
    return int(hour) * 3600 + int(minute) * 60 + float(second)


async def synthesize_one(segment: dict) -> Path:
    AUDIO.mkdir(parents=True, exist_ok=True)
    target = AUDIO / f"{segment['id']}.mp3"
    if target.exists() and target.stat().st_size > 4096:
        return target
    last_error = None
    for attempt in range(4):
        try:
            communicator = edge_tts.Communicate(
                segment["text"],
                "zh-CN-YunxiNeural",
                rate="-6%",
                pitch="-2Hz",
                volume="+4%",
            )
            await asyncio.wait_for(communicator.save(str(target)), timeout=90)
            if target.exists() and target.stat().st_size > 4096:
                return target
        except Exception as error:  # Network TTS occasionally needs a retry.
            last_error = error
            await asyncio.sleep(2 + attempt * 2)
    raise RuntimeError(f"Neural narration failed for {segment['id']}: {last_error}")


async def synthesize_all() -> list[Path]:
    outputs = []
    for segment in SEGMENTS:
        print(f"narration: {segment['id']}")
        outputs.append(await synthesize_one(segment))
    return outputs


def srt_time(seconds: float) -> str:
    milliseconds = round((seconds - int(seconds)) * 1000)
    whole = int(seconds)
    return f"{whole // 3600:02d}:{whole % 3600 // 60:02d}:{whole % 60:02d},{milliseconds:03d}"


def chunks(text: str) -> list[str]:
    sentences = [part.strip() for part in re.split(r"(?<=[。；！？])", text) if part.strip()]
    output: list[str] = []
    for sentence in sentences:
        if len(sentence) <= 28:
            output.append(sentence)
            continue
        buffer = ""
        for part in [p for p in re.split(r"(?<=[，：])", sentence) if p]:
            if buffer and len(buffer + part) > 28:
                output.append(buffer)
                buffer = part
            else:
                buffer += part
        if buffer:
            output.append(buffer)
    return output


def build() -> dict:
    CLIPS.mkdir(parents=True, exist_ok=True)
    audio_paths = asyncio.run(synthesize_all())
    processed_video: list[Path] = []
    processed_audio: list[Path] = []
    subtitle_lines: list[str] = []
    subtitle_index = 1
    timeline = 0.0

    for segment, audio_path in zip(SEGMENTS, audio_paths):
        target = float(segment["duration"])
        source_video = CAPTURES / f"{segment['id']}.webm"
        video_path = CLIPS / f"{segment['id']}.mp4"
        audio_out = AUDIO / f"{segment['id']}.m4a"

        vf = (
            "scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#04090b,"
            "fade=t=in:st=0:d=0.35,"
            f"fade=t=out:st={target - 0.35:.3f}:d=0.35,format=yuv420p"
        )
        run([
            ffmpeg(), "-y", "-stream_loop", "-1", "-i", str(source_video),
            "-t", f"{target:.3f}", "-vf", vf, "-an", "-r", "25",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(video_path),
        ])

        raw_duration = media_duration(audio_path)
        speech_room = target - 1.1
        tempo = max(0.90, min(1.16, raw_duration / speech_room))
        spoken_duration = raw_duration / tempo
        run([
            ffmpeg(), "-y", "-i", str(audio_path),
            "-af", f"atempo={tempo:.6f},adelay=450,apad,loudnorm=I=-17:TP=-1.5:LRA=7",
            "-t", f"{target:.3f}", "-ar", "48000", "-c:a", "aac", "-b:a", "144k", str(audio_out),
        ])

        cue_texts = chunks(segment["text"])
        cue_weights = [max(5, len(cue)) for cue in cue_texts]
        weight_total = sum(cue_weights)
        cursor = timeline + 0.45
        for cue, weight in zip(cue_texts, cue_weights):
            span = spoken_duration * weight / weight_total
            end = min(timeline + target - 0.15, cursor + span)
            subtitle_lines.extend([
                str(subtitle_index),
                f"{srt_time(cursor)} --> {srt_time(end)}",
                cue,
                "",
            ])
            subtitle_index += 1
            cursor = end

        timeline += target
        processed_video.append(video_path)
        processed_audio.append(audio_out)

    SRT.write_text("\n".join(subtitle_lines), encoding="utf-8-sig")
    video_list = BASE / "video_concat.txt"
    audio_list = BASE / "audio_concat.txt"
    video_list.write_text("\n".join(f"file '{p.as_posix()}'" for p in processed_video), encoding="utf-8")
    audio_list.write_text("\n".join(f"file '{p.as_posix()}'" for p in processed_audio), encoding="utf-8")

    visual = BASE / "real_pages.mp4"
    narration = BASE / "natural_narration.m4a"
    run([ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", str(video_list), "-c", "copy", str(visual)])
    run([ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", str(audio_list), "-c", "copy", str(narration)])

    subtitle_filter = (
        "subtitles='" + SRT.relative_to(ROOT).as_posix() + "':"
        "force_style='FontName=Microsoft YaHei,FontSize=16,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&HC0000000,BorderStyle=1,Outline=2,Shadow=0,MarginV=36,Alignment=2'"
    )
    run([
        ffmpeg(), "-y", "-i", str(visual), "-i", str(narration), "-vf", subtitle_filter,
        "-c:v", "libx264", "-preset", "medium", "-crf", "22",
        "-c:a", "aac", "-b:a", "144k", "-movflags", "+faststart", "-shortest", str(OUTPUT),
    ])

    report = {
        "output": str(OUTPUT),
        "duration_seconds": round(media_duration(OUTPUT), 2),
        "size_mb": round(OUTPUT.stat().st_size / 1024 / 1024, 2),
        "resolution": "1920x1080",
        "video": "H.264 / 25fps / real Playwright page captures",
        "audio": "AAC / zh-CN-YunxiNeural / sentence-paced",
        "subtitles": str(SRT),
    }
    (BASE / "build_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
