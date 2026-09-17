"""
Optional Spark implementation sketch.

Run in a Spark-enabled environment after exporting demo tables to Parquet:
spark-submit batch_jobs/spark_jobs/risk_aggregation_spark.py
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def main() -> None:
    spark = SparkSession.builder.appName("agri-risk-aggregation").getOrCreate()
    farms = spark.read.parquet("data/processed/parquet/farms")
    risks = spark.read.parquet("data/processed/parquet/risk_predictions")
    ranking = (
        farms.groupBy("town")
        .agg(F.avg("current_risk_score").alias("avg_risk"), F.count("*").alias("farm_count"))
        .orderBy(F.desc("avg_risk"))
    )
    trend = risks.groupBy("prediction_date").agg(F.avg("risk_score").alias("risk_score")).orderBy("prediction_date")
    ranking.write.mode("overwrite").json("data/processed/spark/town_risk_ranking")
    trend.write.mode("overwrite").json("data/processed/spark/risk_trend")
    spark.stop()


if __name__ == "__main__":
    main()
