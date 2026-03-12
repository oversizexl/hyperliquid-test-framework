#!/usr/bin/env python3
"""运行 pytest 并生成 Allure HTML 报告（Windows 或无 bash 时可用）。每次运行会先清空 allure-results 再写入本次结果。"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)


def run(cmd: list[str], desc: str) -> None:
    print(f">>> {desc}...")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(r.returncode)


def main() -> None:
    # pytest 参数：传脚本后的所有参数给 pytest
    pytest_args = sys.argv[1:] if len(sys.argv) > 1 else []
    run([sys.executable, "-m", "pytest"] + pytest_args, "运行 pytest（结果写入 reports/allure-results）")
    run(
        ["allure", "generate", "reports/allure-results", "-o", "reports/allure-report", "--clean"],
        "生成 Allure HTML 到 reports/allure-report",
    )
    run(["allure", "open", "reports/allure-report"], "打开报告")
    print("HTML 报告位置: reports/allure-report/index.html")


if __name__ == "__main__":
    main()
