"""把参赛需要提交的全部材料打成一个压缩包。

用法（在项目根目录执行）::

    python scripts/build_submission_package.py

前置：先跑 scripts/refresh_submission.ps1 生成最新的文档与 PPT。


产物：
  submission_artifacts/农智云瞰_提交材料_<日期>.zip
    ├─ 01_文档/                 13 份必传说明书 + 概要介绍/详细方案 Word+PDF + 承诺书等
    ├─ 02_演示文档/             项目简介PPT.pptx
    ├─ 03_源代码与可执行程序/   源代码 zip（另含一份解压说明）
    ├─ 04_演示视频/             占位说明（视频需自行录制后放入）
    └─ 提交清单.txt             逐项对照评审系统上传字段
"""
import os, sys, zipfile, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, "submission_artifacts")
FINAL = os.path.join(OUT, "final_upload")

EX_DIRS = {"node_modules", ".next", ".venv", "__pycache__", ".pytest_cache", ".git",
           "artifacts", "submission_artifacts", "runs", "raw", "lake",
           "ip102", "ip102_yolo", "ip102_yolo_runs", "plantdoc", "plantdoc_tar",
           "plantdoc_extracted", "plantdoc_yolo", "plantdoc_yolo_runs", "yolo_runs",
           "yolo_disease_demo", "source_package_staging", "tmp",
           "pptx_qa", "qa_docs", "qa_docx", "qa_pdf", "qa_pdf_formal", "qa_pdf_formal2",
           "qa_pdf_latest", "qa_pdf_latest2", "qa_word_pdf"}
EX_EXT = {".pyc", ".log", ".zip", ".tar", ".gz", ".db"}
EX_FILES = {".env", ".env.local"}

ROOT_FILES = ["README.md", "LICENSE", "Makefile", "pytest.ini", ".env.example",
              "docker-compose.yml", "docker-compose.server.yml", "docker-compose.bigdata.yml",
              "交接说明.md"]
ROOT_DIRS = ["backend", "frontend", "batch_jobs", "knowledge_base", "scripts", "docs",
             "presentation", "data"]


def keep(path_parts, name):
    if any(p in EX_DIRS for p in path_parts):
        return False
    if name in EX_FILES:
        return False
    return os.path.splitext(name)[1].lower() not in EX_EXT


def build_source_zip(target):
    n = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in ROOT_FILES:
            p = os.path.join(ROOT, f)
            if os.path.isfile(p):
                z.write(p, f); n += 1
        for d in ROOT_DIRS:
            base = os.path.join(ROOT, d)
            if not os.path.isdir(base):
                continue
            for cur, dirs, files in os.walk(base):
                dirs[:] = [x for x in dirs if x not in EX_DIRS]
                rel_dir = os.path.relpath(cur, ROOT).replace("\\", "/")
                parts = rel_dir.split("/")
                for fn in files:
                    if not keep(parts, fn):
                        continue
                    z.write(os.path.join(cur, fn), f"{rel_dir}/{fn}")
                    n += 1
    return n, os.path.getsize(target)


def main():
    stamp = datetime.date.today().strftime("%Y%m%d")
    src_zip = os.path.join(OUT, "云穗智擎_山东建筑大学_张衡_源代码与可执行程序.zip")
    print("[1/3] 打包源代码 ...", flush=True)
    n, size = build_source_zip(src_zip)
    print(f"      {n} 个文件，{size/1024/1024:.1f} MB", flush=True)

    master = os.path.join(OUT, f"农智云瞰_提交材料_{stamp}.zip")
    print("[2/3] 组装总包 ...", flush=True)
    docs, ppt = [], []
    for fn in sorted(os.listdir(FINAL)):
        if fn.endswith((".mp4", ".zip")):
            continue  # 视频与源码包各有专属目录，不重复放进 01_文档
        (ppt if fn.endswith(".pptx") else docs).append(fn)

    with zipfile.ZipFile(master, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for fn in docs:
            z.write(os.path.join(FINAL, fn), f"01_文档/{fn}")
        for fn in ppt:
            z.write(os.path.join(FINAL, fn), f"02_演示文档/{fn}")
        z.write(src_zip, f"03_源代码与可执行程序/{os.path.basename(src_zip)}")
        video = os.path.join(FINAL, "云穗智擎_山东建筑大学_张衡_项目演示视频.mp4")
        if os.path.exists(video):
            z.write(video, "04_演示视频/" + os.path.basename(video))
        else:
            z.writestr("04_演示视频/请把录好的视频放在这里.txt",
                       "演示视频要求（赛题通知原文）：\n"
                       "  · 格式 MP4\n"
                       "  · 大小不超过 200MB\n"
                       "  · 时长不超过 8 分钟\n"
                       "  · 命名 云穗智擎_山东建筑大学_张衡_项目演示视频.mp4\n\n"
                       "录制脚本见 01_文档 同级项目仓库 docs/演示视频脚本.md。\n")
        z.writestr("提交清单.txt", CHECKLIST.format(stamp=stamp, n=n, mb=size/1024/1024))
    print(f"[3/3] 完成：{master}", flush=True)
    print(f"      总包大小 {os.path.getsize(master)/1024/1024:.1f} MB")


CHECKLIST = """农智云瞰 · 提交材料清单
=====================================================
生成日期：{stamp}
赛事：山东省大学生软件设计大赛
赛题：大数据与人工智能行业应用开发（命题单位：山东中医药大学 / 命题老师：马金刚）
作品：农智云瞰——面向县域农业的农情大数据分析与病虫害风险挖掘平台

团队：云穗智擎 | 山东建筑大学 计算机与人工智能学院 | 队长 张衡 | 指导教师 刘新锋
作品版本：v1.0.0 | 作品访问地址：http://47.105.74.222:3001/login | 计划提交日期：2026-09-19
全部文件已按通知规定命名为 云穗智擎_山东建筑大学_张衡_材料名。

-----------------------------------------------------
一、评审系统必传项与本包对应关系
-----------------------------------------------------
上传字段              格式        本包位置
需求分析说明书        doc|docx    01_文档/..._需求分析说明书.docx
概要设计说明书        doc|docx    01_文档/..._概要设计说明书.docx
数据库设计说明书      doc|docx    01_文档/..._数据库设计说明书.docx
详细设计说明书        doc|docx    01_文档/..._详细设计说明书.docx
安装部署说明书        doc|docx    01_文档/..._安装部署说明书.docx
软件使用说明书        doc|docx    01_文档/..._软件使用说明书.docx
测试文档              doc|docx    01_文档/..._测试文档.docx
工作计划              doc|docx    01_文档/..._工作计划.docx
会议纪要              doc|docx    01_文档/..._会议纪要.docx
工作总结              doc|docx    01_文档/..._工作总结.docx
源代码                zip|rar     03_源代码与可执行程序/..._源代码与可执行程序.zip
源代码网盘地址&提取码 文本框      ★ 待填写：把上面的 zip 上传网盘后填链接与提取码
演示文档              ppt|pptx    02_演示文档/..._项目简介PPT.pptx
演示视频              mp4         ★ 待录制：放入 04_演示视频/

-----------------------------------------------------
二、通知要求的其他材料
-----------------------------------------------------
作品名称 / 作品简介(300-500字) / 行业领域与应用场景
    → 报名系统在线填写，文案见 01_文档/..._作品基本信息登记表.docx
      与项目仓库 docs/项目简介_300-500字.md（496 字）
项目概要介绍（Word + PDF，不超过 1500 字）
    → 01_文档/..._项目概要介绍.docx / .pdf（1495 字）
项目详细方案（Word + PDF）
    → 01_文档/..._项目详细方案.docx / .pdf
竞赛承诺书（须签署）
    → 01_文档/..._竞赛承诺书.docx　★ 打印、全员及指导教师签字、盖章后扫描
数据集说明（可选）
    → 01_文档/..._数据集说明.docx
其他证明材料（可选）
    → 01_文档/..._开源组件与协议说明.docx

-----------------------------------------------------
三、源代码包内容（共 {n} 个文件，{mb:.1f} MB）
-----------------------------------------------------
backend/          FastAPI 后端、ML 模型、RAG 检索
frontend/         Next.js 前端
batch_jobs/       Spark ETL 主链路 + Hive DDL + pandas 参考实现
scripts/          造数、训练、文档与 PPT 生成、口径比对
knowledge_base/   本地农技知识库
docs/             全部工程文档 Markdown 源
data/generated/models/  已训练模型权重（可直接部署运行）
docker-compose*.yml     在线系统 + Spark 大数据环境两套编排
已排除：node_modules、.venv、__pycache__、原始训练数据集、运行日志、.env 密钥文件

-----------------------------------------------------
四、上传前自检
-----------------------------------------------------
[ ] 文件名占位已全部替换为正式团队信息
[ ] 竞赛承诺书已签字盖章并扫描
[ ] 源代码 zip 已上传网盘，链接长期有效、无需登录即可下载
[ ] 演示视频为 MP4、不超过 200MB、不超过 8 分钟
[ ] PPT 第 15 页两处界面截图已替换，第 19 页团队信息已填写
[ ] 源代码包中不含 .env 真实密钥（本包已自动排除）
[ ] 队伍 1-5 人且全部同校，指导教师不超过 2 人
"""

if __name__ == "__main__":
    main()
