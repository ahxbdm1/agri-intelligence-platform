from __future__ import annotations

import json
import random
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_ROOT = PROJECT_ROOT / "data" / "raw" / "plantdoc_tar" / "PlantDoc-Object-Detection-Dataset-master"
DATASET_ROOT = PROJECT_ROOT / "data" / "generated" / "plantdoc_yolo"
RUNS_ROOT = PROJECT_ROOT / "data" / "generated" / "plantdoc_yolo_runs"
MODEL_ROOT = PROJECT_ROOT / "data" / "generated" / "models"
SEED = 20260820


def _text(node: ET.Element | None, default: str = "") -> str:
    return " ".join((node.text or default).split()) if node is not None else default


def _find_image(xml_path: Path) -> Path | None:
    candidates = [xml_path.with_suffix(ext) for ext in (".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG")]
    return next((path for path in candidates if path.exists()), None)


def _parse_annotation(xml_path: Path) -> tuple[str, int, int, list[tuple[str, float, float, float, float]]]:
    root = ET.parse(xml_path).getroot()
    filename = _text(root.find("filename"), xml_path.stem)
    size = root.find("size")
    width = int(float(_text(size.find("width"), "1"))) if size is not None else 1
    height = int(float(_text(size.find("height"), "1"))) if size is not None else 1
    boxes = []
    for obj in root.findall("object"):
        name = _text(obj.find("name"), "unknown")
        box = obj.find("bndbox")
        if box is None:
            continue
        xmin = max(0.0, min(float(_text(box.find("xmin"), "0")), width))
        ymin = max(0.0, min(float(_text(box.find("ymin"), "0")), height))
        xmax = max(0.0, min(float(_text(box.find("xmax"), "0")), width))
        ymax = max(0.0, min(float(_text(box.find("ymax"), "0")), height))
        if xmax <= xmin or ymax <= ymin:
            continue
        boxes.append((name, (xmin + xmax) / 2 / width, (ymin + ymax) / 2 / height, (xmax - xmin) / width, (ymax - ymin) / height))
    return filename, width, height, boxes


def prepare_dataset() -> tuple[Path, list[str], dict[str, int]]:
    if not RAW_ROOT.exists():
        raise FileNotFoundError(f"PlantDoc 数据未找到：{RAW_ROOT}")
    if DATASET_ROOT.exists():
        shutil.rmtree(DATASET_ROOT)
    for split in ("train", "val"):
        (DATASET_ROOT / "images" / split).mkdir(parents=True, exist_ok=True)
        (DATASET_ROOT / "labels" / split).mkdir(parents=True, exist_ok=True)

    records: list[tuple[str, Path, list[tuple[str, float, float, float, float]]]] = []
    class_names: set[str] = set()
    for source_split, target_split in (("TRAIN", "train"), ("TEST", "val")):
        for xml_path in sorted((RAW_ROOT / source_split).glob("*.xml")):
            image_path = _find_image(xml_path)
            if image_path is None:
                continue
            _, _, _, boxes = _parse_annotation(xml_path)
            if not boxes:
                continue
            class_names.update(item[0] for item in boxes)
            records.append((target_split, image_path, boxes))

    names = sorted(class_names)
    label_map = {name: index for index, name in enumerate(names)}
    counts = {"train_images": 0, "val_images": 0, "train_boxes": 0, "val_boxes": 0, "skipped_images": 0}
    for index, (split, image_path, boxes) in enumerate(records):
        stem = f"{split}_{index:05d}"
        target_image = DATASET_ROOT / "images" / split / f"{stem}{image_path.suffix.lower()}"
        target_label = DATASET_ROOT / "labels" / split / f"{stem}.txt"
        try:
            shutil.copy2(image_path, target_image)
            target_label.write_text(
                "\n".join(f"{label_map[name]} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}" for name, cx, cy, bw, bh in boxes),
                encoding="utf-8",
            )
        except OSError:
            counts["skipped_images"] += 1
            continue
        counts[f"{split}_images"] += 1
        counts[f"{split}_boxes"] += len(boxes)

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
                "dataset": "PlantDoc Object Detection Dataset",
                "source": "https://github.com/pratikkayal/PlantDoc-Object-Detection-Dataset",
                "license": "CC BY 4.0",
                "citation": "Singh et al., PlantDoc: A Dataset for Visual Plant Disease Detection, 2020",
                "task": "real-image plant disease object detection",
                "classes": names,
                "counts": counts,
                "note": "数据来自公开数据集，不能替代山东本地田间数据验证；正式应用需增加本地样本和专家复核。",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return yaml_path, names, counts


def main() -> None:
    from ultralytics import YOLO

    random.seed(SEED)
    yaml_path, names, counts = prepare_dataset()
    MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(PROJECT_ROOT / "yolo11n.pt"))
    results = model.train(
        data=str(yaml_path),
        epochs=35,
        imgsz=512,
        batch=16,
        device=0,
        workers=0,
        project=str(RUNS_ROOT),
        name="plantdoc_v1",
        exist_ok=True,
        seed=SEED,
        patience=10,
        pretrained=True,
        verbose=False,
    )
    best_path = Path(results.save_dir) / "weights" / "best.pt"
    target = MODEL_ROOT / "plantdoc_yolo_best.pt"
    shutil.copy2(best_path, target)
    classes_path = target.with_suffix(".classes.json")
    classes_path.write_text(json.dumps(names, ensure_ascii=False, indent=2), encoding="utf-8")
    metrics = model.val(data=str(yaml_path), imgsz=512, batch=16, device=0, workers=0, verbose=False)
    metrics_path = target.with_suffix(".metrics.json")
    metrics_path.write_text(
        json.dumps(
            {
                "model": "YOLO11n",
                "dataset": "PlantDoc Object Detection Dataset",
                "dataset_source": "https://github.com/pratikkayal/PlantDoc-Object-Detection-Dataset",
                "license": "CC BY 4.0",
                "train_images": counts["train_images"],
                "val_images": counts["val_images"],
                "train_boxes": counts["train_boxes"],
                "val_boxes": counts["val_boxes"],
                "classes": len(names),
                "device": "cuda:0",
                "map50": round(float(metrics.box.map50), 4),
                "map50_95": round(float(metrics.box.map), 4),
                "precision": round(float(metrics.box.mp), 4),
                "recall": round(float(metrics.box.mr), 4),
                "warning": "指标来自公开 PlantDoc 验证集，不代表山东本地田间泛化能力；上线前需使用本地标注数据复测。",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"weights": str(target), "metrics": str(metrics_path), "classes": len(names)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
