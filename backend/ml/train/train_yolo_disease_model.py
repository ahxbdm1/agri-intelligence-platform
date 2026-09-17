from __future__ import annotations

from pathlib import Path
import random
import shutil
import sys

from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from ml.disease_classifier import DISEASE_LIBRARY  # noqa: E402

SEED = 20260820
IMAGE_SIZE = 128
SAMPLES_PER_CLASS = 100


def make_sample(label: int, sample: int) -> tuple[Image.Image, list[tuple[int, int, int, int]]]:
    rng = random.Random(SEED + label * 1000 + sample)
    image = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), (28 + rng.randrange(20), 92 + rng.randrange(34), 42 + rng.randrange(24)))
    draw = ImageDraw.Draw(image, "RGBA")
    leaf_box = (12, 12, 116, 116)
    draw.ellipse(leaf_box, fill=(48, 145 + rng.randrange(25), 58, 255), outline=(164, 220, 132, 220), width=2)
    boxes: list[tuple[int, int, int, int]] = []
    colors = [(92, 46, 30, 220), (218, 132, 88, 210), (103, 48, 36, 220), (92, 46, 30, 220), (228, 204, 56, 210)]
    for _ in range(2 + rng.randrange(3)):
        x, y = rng.randrange(28, 96), rng.randrange(26, 96)
        width, height = 8 + rng.randrange(10), 7 + rng.randrange(10)
        color = colors[label]
        if label == 3:
            height = 4 + rng.randrange(5)
        draw.ellipse((x, y, x + width, y + height), fill=color)
        boxes.append((x, y, x + width, y + height))
    return image, boxes


def write_dataset(dataset_dir: Path) -> Path:
    if dataset_dir.exists():
        shutil.rmtree(dataset_dir)
    for split in ("train", "val"):
        (dataset_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (dataset_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    for label in range(len(DISEASE_LIBRARY)):
        for sample in range(SAMPLES_PER_CLASS):
            split = "val" if sample >= int(SAMPLES_PER_CLASS * 0.8) else "train"
            image, boxes = make_sample(label, sample)
            stem = f"class_{label}_{sample:04d}"
            image.save(dataset_dir / "images" / split / f"{stem}.png")
            lines = []
            for x1, y1, x2, y2 in boxes:
                cx = ((x1 + x2) / 2) / IMAGE_SIZE
                cy = ((y1 + y2) / 2) / IMAGE_SIZE
                width = (x2 - x1) / IMAGE_SIZE
                height = (y2 - y1) / IMAGE_SIZE
                lines.append(f"{label} {cx:.6f} {cy:.6f} {width:.6f} {height:.6f}")
            (dataset_dir / "labels" / split / f"{stem}.txt").write_text("\n".join(lines), encoding="utf-8")

    data_yaml = dataset_dir / "data.yaml"
    names = [item["disease_name"] for item in DISEASE_LIBRARY]
    data_yaml.write_text(
        "path: " + dataset_dir.as_posix() + "\n" +
        "train: images/train\nval: images/val\n" +
        f"nc: {len(names)}\n" +
        "names: " + str(names).replace("'", "\"") + "\n",
        encoding="utf-8",
    )
    return data_yaml


def main() -> None:
    from ultralytics import YOLO

    dataset_dir = PROJECT_ROOT / "data" / "generated" / "yolo_disease_demo"
    data_yaml = write_dataset(dataset_dir)
    runs_dir = PROJECT_ROOT / "data" / "generated" / "yolo_runs"
    model = YOLO("yolo11n.pt")
    results = model.train(
        data=str(data_yaml),
        epochs=20,
        imgsz=320,
        batch=16,
        device=0,
        workers=0,
        project=str(runs_dir),
        name="disease_demo",
        exist_ok=True,
        seed=SEED,
        patience=8,
        verbose=False,
    )
    best_path = Path(results.save_dir) / "weights" / "best.pt"
    target = PROJECT_ROOT / "data" / "generated" / "models" / "disease_yolo_best.pt"
    shutil.copy2(best_path, target)
    metrics = model.val(data=str(data_yaml), imgsz=320, batch=16, device=0, workers=0, verbose=False)
    metrics_path = target.with_name("disease_yolo_metrics.json")
    metrics_path.write_text(
        __import__("json").dumps(
            {
                "model": "yolo11n",
                "dataset": "synthetic-leaf-detection-v1",
                "train_samples": len(DISEASE_LIBRARY) * int(SAMPLES_PER_CLASS * 0.8),
                "val_samples": len(DISEASE_LIBRARY) * int(SAMPLES_PER_CLASS * 0.2),
                "device": "cuda:0",
                "map50": round(float(metrics.box.map50), 4),
                "map50_95": round(float(metrics.box.map), 4),
                "precision": round(float(metrics.box.mp), 4),
                "recall": round(float(metrics.box.mr), 4),
                "warning": "指标来自程序生成的合成叶片数据，不代表真实田间泛化能力。",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print({"weights": str(target), "metrics": str(metrics_path), "map50": float(metrics.box.map50), "map50_95": float(metrics.box.map)})


if __name__ == "__main__":
    main()
