# 重新生成全部参赛提交物，并清理旧版本文件。
#
# 用法（在项目根目录执行）：
#   .\scripts\refresh_submission.ps1
#
# 团队信息已写入文档与构建脚本（云穗智擎 / 山东建筑大学 / 队长 张衡），
# 生成的文件名直接符合赛题通知规定格式：团队名称_学校名称_队长姓名_材料名。
# 如需临时换成其他团队信息，可传三个参数覆盖文件名：
#   .\scripts\refresh_submission.ps1 -TeamName "X" -School "Y" -Leader "Z"

param(
    [string]$TeamName = "",
    [string]$School = "",
    [string]$Leader = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "py -3.11" }

Write-Host "== 1/6 清理上一版提交物 =="
$artifacts = Join-Path $root "submission_artifacts"
$final = Join-Path $artifacts "final_upload"
New-Item -ItemType Directory -Force -Path $artifacts, $final | Out-Null
Get-ChildItem -Path $artifacts -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -in ".docx", ".pdf", ".pptx" } |
    Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $final -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -in ".docx", ".pdf", ".pptx" } |
    Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "== 2/6 刷新文档索引 =="
& $py scripts\build_docs.py

Write-Host "== 3/6 生成 Word / PDF =="
& $py scripts\build_submission_artifacts.py

Write-Host "== 4/6 生成 PPT =="
& $py scripts\build_pptx.py

Write-Host "== 5/6 同步到 final_upload =="
Get-ChildItem -Path $artifacts -File | Where-Object { $_.Extension -in ".docx", ".pdf", ".pptx" } |
    Copy-Item -Destination $final -Force

if ($TeamName -and $School -and $Leader) {
    Write-Host "== 覆盖文件名：$TeamName / $School / $Leader =="
    Get-ChildItem -Path $final -File | ForEach-Object {
        $newName = $_.Name.Replace("云穗智擎", $TeamName).Replace("山东建筑大学", $School).Replace("张衡", $Leader)
        if ($newName -ne $_.Name) { Rename-Item -Path $_.FullName -NewName $newName }
    }
}

Write-Host "== 6/6 打包提交材料 =="
& $py scripts\build_submission_package.py

Write-Host ""
Write-Host "完成。最终上传目录：$final" -ForegroundColor Green
Get-ChildItem -Path $final -File | Select-Object Name, @{N = "KB"; E = { [math]::Round($_.Length / 1KB, 1) } } | Format-Table -AutoSize

Write-Host "仍需人工完成：" -ForegroundColor Yellow
Write-Host "  1. 打印《竞赛承诺书》，6 人手写签名 + 学院/学校盖章后扫描为 PDF" -ForegroundColor Yellow
Write-Host "  2. 把源代码 zip 上传网盘，回填地址与提取码" -ForegroundColor Yellow
Write-Host "  3. 录制演示视频：MP4，不超过 200MB，不超过 8 分钟" -ForegroundColor Yellow
Write-Host "  4. 替换 PPT 第 15 页的两处界面截图" -ForegroundColor Yellow
