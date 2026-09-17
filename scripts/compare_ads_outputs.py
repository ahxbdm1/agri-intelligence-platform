"""比对 Spark 主链路与 pandas 参考实现的 ADS 产出，验证指标口径一致。

在测试环节运行：两条链路读同一份 ODS 数据、使用同一套清洗规则与风险评分公式，
除浮点舍入外结果应逐字段相同。任何一侧改动口径都会被本脚本立即发现。

用法::

    python batch_jobs/pandas_jobs/ads_reference_job.py          # 产生参考结果
    docker compose -f docker-compose.bigdata.yml run --rm spark-local   # 产生 Spark 结果
    python scripts/compare_ads_outputs.py                       # 比对

退出码 0 表示全部一致，1 表示存在差异（差异明细打印到标准输出）。
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TABLES = [
    "ads_town_risk_ranking",
    "ads_crop_risk_distribution",
    "ads_risk_trend_30d",
    "ads_yield_summary",
    "ads_inspection_priority",
    "ads_material_dispatch",
]
TOLERANCE = 0.02  # 允许的浮点绝对误差，覆盖两侧 round 实现差异


def load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def same_value(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a is None or b is None:
            return a == b
        if isinstance(a, float) and math.isnan(a) and isinstance(b, float) and math.isnan(b):
            return True
        return abs(float(a) - float(b)) <= TOLERANCE
    return str(a) == str(b)


def compare_table(name: str, spark_rows: list[dict], ref_rows: list[dict]) -> list[str]:
    issues: list[str] = []
    if len(spark_rows) != len(ref_rows):
        issues.append(f"{name}: 行数不一致 spark={len(spark_rows)} reference={len(ref_rows)}")
        return issues
    for i, (s, r) in enumerate(zip(spark_rows, ref_rows)):
        keys = set(s) | set(r)
        for k in sorted(keys):
            if k not in s or k not in r:
                issues.append(f"{name}[{i}]: 字段缺失 {k}")
                continue
            if not same_value(s[k], r[k]):
                issues.append(f"{name}[{i}].{k}: spark={s[k]!r} reference={r[k]!r}")
    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="ADS 口径一致性比对")
    parser.add_argument("--spark", default="data/lake/ads")
    parser.add_argument("--reference", default="data/lake/ads_reference")
    args = parser.parse_args()

    spark_dir = PROJECT_ROOT / args.spark
    ref_dir = PROJECT_ROOT / args.reference

    all_issues: list[str] = []
    checked = 0
    for table in TABLES:
        sp, rf = spark_dir / f"{table}.json", ref_dir / f"{table}.json"
        if not sp.exists():
            all_issues.append(f"{table}: 缺少 Spark 产出 {sp}")
            continue
        if not rf.exists():
            all_issues.append(f"{table}: 缺少参考产出 {rf}")
            continue
        all_issues.extend(compare_table(table, load(sp), load(rf)))
        checked += 1

    if all_issues:
        print(f"发现 {len(all_issues)} 处差异（已比对 {checked}/{len(TABLES)} 张表）：")
        for issue in all_issues[:80]:
            print("  -", issue)
        if len(all_issues) > 80:
            print(f"  ... 其余 {len(all_issues) - 80} 处省略")
        sys.exit(1)

    print(f"OK: {checked} 张 ADS 表在 Spark 主链路与 pandas 参考实现之间完全一致（容差 {TOLERANCE}）")


if __name__ == "__main__":
    main()
