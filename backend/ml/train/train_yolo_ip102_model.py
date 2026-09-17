from __future__ import annotations

import json
import os
import random
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
VOC_ROOT = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "ip102"
    / "Detection-official-extracted"
    / "Detection"
    / "VOC2007"
)
CLASSES_PATH = PROJECT_ROOT / "data" / "raw" / "ip102" / "Classification" / "classes.txt"
DATASET_ROOT = PROJECT_ROOT / "data" / "generated" / "ip102_yolo"
RUNS_ROOT = PROJECT_ROOT / "data" / "generated" / "ip102_yolo_runs"
MODEL_ROOT = PROJECT_ROOT / "data" / "generated" / "models"
SEED = 20260828


def read_classes() -> list[str]:
    """Read the official 1-based class list and convert it to YOLO's 0-based order."""
    if not CLASSES_PATH.exists():
        raise FileNotFoundError(f"IP102 类别文件不存在：{CLASSES_PATH}")
    entries: list[tuple[int, str]] = []
    pattern = re.compile(r"^\s*(\d+)\s+(.+?)\s*$")
    for line in CLASSES_PATH.read_text(encoding="utf-8-sig").splitlines():
        match = pattern.match(line)
        if match:
            entries.append((int(match.group(1)), " ".join(match.group(2).split())))
    entries.sort(key=lambda item: item[0])
    names = [name for _, name in entries]
    if len(names) != 102:
        raise ValueError(f"IP102 类别数量异常：期望 102，实际 {len(names)}")
    return names


def read_split(filename: str) -> list[str]:
    split_path = VOC_ROOT / "ImageSets" / "Main" / filename
    if not split_path.exists():
        raise FileNotFoundError(f"IP102 划分文件不存在：{split_path}")
    return [line.strip().split()[0] for line in split_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def _number(node: ET.Element | None, default: float = 0.0) -> float:
    try:
        return float((node.text or "").strip()) if node is not None else default
    except (TypeError, ValueError):
        return default


def parse_annotation(xml_path: Path, class_count: int) -> tuple[int, int, list[tuple[int, float, float, float, float]]]:
    root = ET.parse(xml_path).getroot()
    size = root.find("size")
    width = max(1.0, _number(size.find("width") if size is not None else None, 1.0))
    height = max(1.0, _number(size.find("height") if size is not None else None, 1.0))
    boxes: list[tuple[int, float, float, float, float]] = []
    for obj in root.findall("object"):
        raw_name = (obj.findtext("name") or "").strip()
        try:
            class_id = int(raw_name)
        except ValueError:
            continue
        # Official IP102 VOC files use 0..101. Accept 1..102 as a defensive fallback.
        if class_id == class_count:
            class_id -= 1
        if class_id < 0 or class_id >= class_count:
            continue
        box = obj.find("bndbox")
        if box is None:
            continue
        xmin = max(0.0, min(_number(box.find("xmin")), width))
        ymin = max(0.0, min(_number(box.find("ymin")), height))
        xmax = max(0.0, min(_number(box.find("xmax")), width))
        ymax = max(0.0, min(_number(box.find("ymax")), height))
        if xmax <= xmin or ymax <= ymin:
            continue
        boxes.append(
            (
                class_id,
                (xmin + xmax) / 2.0 / width,
                (ymin + ymax) / 2.0 / height,
                (xmax - xmin) / width,
                (ymax - ymin) / height,
            )
        )
    return int(width), int(height), boxes


def prepare_dataset(names: list[str]) -> dict[str, int]:
    if not VOC_ROOT.exists():
        raise FileNotFoundError(f"IP102 VOC 数据未找到：{VOC_ROOT}")
    image_root = VOC_ROOT / "JPEGImages"
    annotation_root = VOC_ROOT / "Annotations"
    if not image_root.exists() or not annotation_root.exists():
        raise FileNotFoundError("IP102 JPEGImages 或 Annotations 尚未解压")

    if DATASET_ROOT.exists():
        shutil.rmtree(DATASET_ROOT)
    for split in ("train", "val"):
        (DATASET_ROOT / "images" / split).mkdir(parents=True, exist_ok=True)
        (DATASET_ROOT / "labels" / split).mkdir(parents=True, exist_ok=True)

    split_ids = {"train": read_split("trainval.txt"), "val": read_split("test.txt")}
    counts = {
        "train_images": 0,
        "val_images": 0,
        "train_boxes": 0,
        "val_boxes": 0,
        "skipped_images": 0,
        "skipped_annotations": 0,
    }
    class_counts = [0] * len(names)

    for split, ids in split_ids.items():
        for index, image_id in enumerate(ids):
            xml_path = annotation_root / f"{image_id}.xml"
            image_path = image_root / f"{image_id}.jpg"
            if not xml_path.exists() or not image_path.exists():
                counts["skipped_images"] += 1
                continue
            try:
                _, _, boxes = parse_annotation(xml_path, len(names))
            except (ET.ParseError, OSError):
                counts["skipped_annotations"] += 1
                continue
            if not boxes:
                counts["skipped_annotations"] += 1
                continue

            target_stem = f"{split}_{index:05d}_{image_id}"
            target_image = DATASET_ROOT / "images" / split / f"{target_stem}.jpg"
            target_label = DATASET_ROOT / "labels" / split / f"{target_stem}.txt"
            shutil.copy2(image_path, target_image)
            target_label.write_text(
                "\n".join(
                    f"{class_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}"
                    for class_id, cx, cy, bw, bh in boxes
                ),
                encoding="utf-8",
            )
            counts[f"{split}_images"] += 1
            counts[f"{split}_boxes"] += len(boxes)
            for class_id, *_ in boxes:
                class_counts[class_id] += 1

    yaml_path = DATASET_ROOT / "data.yaml"
    yaml_path.write_text(
        f"path: {DATASET_ROOT.as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        f"nc: {len(names)}\n"
        f"names: {json.dumps(names, ensure_ascii=False)}\n",
        encoding="utf-8",
    )
    (DATASET_ROOT / "classes.json").write_text(json.dumps(names, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATASET_ROOT / "dataset_card.json").write_text(
        json.dumps(
            {
                "dataset": "IP102",
                "task": "102-class insect pest object detection",
                "source": "https://github.com/xpwu95/IP102",
                "license_note": "官方仓库说明主要用于学术研究；正式商用或对外服务前需核对原作者授权。",
                "classes": names,
                "counts": counts,
                "class_box_counts": {names[i]: count for i, count in enumerate(class_counts)},
                "split_policy": "trainval.txt 用于训练，test.txt 仅用于最终评估。",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"dataset": str(DATASET_ROOT), "classes": len(names), **counts}, ensure_ascii=False))
    return counts


def main() -> None:
    from ultralytics import YOLO

    random.seed(SEED)
    names = read_classes()
    counts = prepare_dataset(names)
    MODEL_ROOT.mkdir(parents=True, exist_ok=True)

    epochs = int(os.getenv("IP102_EPOCHS", "30"))
    imgsz = int(os.getenv("IP102_IMGSZ", "640"))
    batch = int(os.getenv("IP102_BATCH", "8"))
    device = os.getenv("IP102_DEVICE", "0")
    model = YOLO(str(PROJECT_ROOT / "yolo11n.pt"))
    results = model.train(
        data=str(DATASET_ROOT / "data.yaml"),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        workers=0,
        cache=False,
        amp=True,
        project=str(RUNS_ROOT),
        name="ip102_yolo11n_v1",
        exist_ok=True,
        seed=SEED,
        patience=8,
        pretrained=True,
        verbose=False,
    )

    best_path = Path(results.save_dir) / "weights" / "best.pt"
    target = MODEL_ROOT / "ip102_pest_yolo_best.pt"
    shutil.copy2(best_path, target)
    target.with_suffix(".classes.json").write_text(json.dumps(names, ensure_ascii=False, indent=2), encoding="utf-8")

    # The official test split is mapped to val in data.yaml and is never used for fitting.
    metrics = model.val(
        data=str(DATASET_ROOT / "data.yaml"),
        split="val",
        imgsz=imgsz,
        batch=batch,
        device=device,
        workers=0,
        verbose=False,
    )
    metrics_payload = {
        "model": "YOLO11n",
        "model_version": "yolo-ip102-v1",
        "dataset": "IP102 official Detection VOC",
        "dataset_source": "https://github.com/xpwu95/IP102",
        "classes": len(names),
        "train_images": counts["train_images"],
        "test_images": counts["val_images"],
        "train_boxes": counts["train_boxes"],
        "test_boxes": counts["val_boxes"],
        "epochs": epochs,
        "imgsz": imgsz,
        "batch": batch,
        "device": str(device),
        "map50": round(float(metrics.box.map50), 4),
        "map50_95": round(float(metrics.box.map), 4),
        "precision": round(float(metrics.box.mp), 4),
        "recall": round(float(metrics.box.mr), 4),
        "note": "测试指标来自 IP102 官方 test.txt；不代表山东本地田间泛化准确率，正式部署前需使用本地样本复测。",
    }
    metrics_path = target.with_suffix(".metrics.json")
    metrics_path.write_text(json.dumps(metrics_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"weights": str(target), "metrics": str(metrics_path), **metrics_payload}, ensure_ascii=False))


if __name__ == "__main__":
    main()
