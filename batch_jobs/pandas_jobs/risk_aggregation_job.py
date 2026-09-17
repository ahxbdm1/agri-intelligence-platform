from __future__ import annotations

from pathlib import Path
import json
import sqlite3

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "agri_intelligence.db"
OUT_DIR = PROJECT_ROOT / "data" / "processed"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"数据库不存在，请先运行 python scripts/generate_demo_data.py: {DB_PATH}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    farms = pd.read_sql_query(
        """
        select f.id, f.name, f.town, f.area_mu, f.current_risk_score, f.risk_level, c.name as crop
        from farms f join crops c on c.id = f.crop_id
        """,
        conn,
    )
    risks = pd.read_sql_query("select farm_id, prediction_date, risk_score, risk_level from risk_predictions", conn)
    yields = pd.read_sql_query("select farm_id, year, predicted_yield_kg_per_mu, loss_rate from yield_records", conn)
    tasks = pd.read_sql_query("select farm_id, priority, status, due_date from inspection_tasks", conn)

    town_ranking = (
        farms.groupby("town")
        .agg(avg_risk=("current_risk_score", "mean"), high_risk_farms=("risk_level", lambda s: int((s == "高").sum())), area_mu=("area_mu", "sum"))
        .reset_index()
        .sort_values("avg_risk", ascending=False)
    )
    crop_distribution = farms.groupby(["crop", "risk_level"]).size().reset_index(name="count")
    future_trend = risks.sort_values("prediction_date").groupby("prediction_date").agg(risk_score=("risk_score", "mean")).tail(7).reset_index()
    yield_prediction = yields.groupby("year").agg(predicted_yield=("predicted_yield_kg_per_mu", "mean"), avg_loss_rate=("loss_rate", "mean")).reset_index()
    task_priority = tasks.groupby(["priority", "status"]).size().reset_index(name="count")

    dispatch = []
    for _, row in town_ranking.head(3).iterrows():
        dispatch.append(
            {
                "town": row["town"],
                "recommendation": f"向{row['town']}优先调度植保无人机、农技员和高湿病害防控药剂，覆盖约 {row['area_mu']:.0f} 亩。",
                "reason": f"平均风险评分 {row['avg_risk']:.1f}，高风险地块 {int(row['high_risk_farms'])} 个。",
            }
        )

    summary = {
        "town_risk_ranking": town_ranking.to_dict(orient="records"),
        "crop_risk_distribution": crop_distribution.to_dict(orient="records"),
        "future_7d_risk_trend": future_trend.to_dict(orient="records"),
        "yield_prediction": yield_prediction.to_dict(orient="records"),
        "inspection_task_priority": task_priority.to_dict(orient="records"),
        "agri_material_dispatch": dispatch,
    }
    town_ranking.to_csv(OUT_DIR / "town_risk_ranking.csv", index=False, encoding="utf-8-sig")
    (OUT_DIR / "agri_batch_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUT_DIR), "towns": len(town_ranking), "dispatch_items": len(dispatch)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
