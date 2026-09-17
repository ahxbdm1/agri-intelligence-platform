from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    docs = PROJECT_ROOT / "docs"
    required = [
        "项目概要介绍.md",
        "项目详细方案.md",
        "项目简介_300-500字.md",
        "需求分析说明书.md",
        "数据库设计说明书.md",
        "概要设计说明书.md",
        "详细设计说明书.md",
        "安装部署说明.md",
        "使用说明.md",
        "数据集说明.md",
        "开源组件与协议说明.md",
        "测试报告.md",
        "工作计划.md",
        "会议纪要.md",
        "工作总结.md",
        "作品基本信息登记表.md",
        "演示视频脚本.md",
        "答辩问题准备.md",
        "PPT大纲.md",
        "参赛提交清单.md",
        "正式提交材料准备说明.md",
        "现场演示与部署核验清单.md",
        "竞赛承诺书.md",
    ]
    missing = [name for name in required if not (docs / name).exists()]
    if missing:
        raise FileNotFoundError(f"文档缺失: {missing}")
    index = ["# 农智云瞰文档索引\n"]
    for name in required:
        index.append(f"- [{name}](./{name})")
    (docs / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(f"Docs index generated: {docs / 'README.md'}")


if __name__ == "__main__":
    main()
