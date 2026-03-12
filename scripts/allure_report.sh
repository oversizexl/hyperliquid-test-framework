#!/usr/bin/env bash
# 运行测试并生成 Allure HTML 报告（保留历次 allure-results，仅重新生成 report 目录）
set -e
cd "$(dirname "$0")/.."

echo ">>> 运行 pytest（会先清空 reports/allure-results，再写入本次结果）..."
pytest "$@"
echo ">>> 生成 Allure HTML 到 reports/allure-report ..."
allure generate reports/allure-results -o reports/allure-report --clean
echo ">>> 打开报告（可手动打开 reports/allure-report/index.html）..."
allure open reports/allure-report
