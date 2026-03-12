#!/usr/bin/env python
"""
根据简单的命令行参数生成测试用例骨架，减少样板代码。

使用示例：

    python scripts/new_test_case.py \\
      --name get_positions \\
      --marker position \\
      --feature "仓位" \\
      --story "查询仓位" \\
      --title "查询仓位列表结构正确"

默认会在 tests/ 目录下生成文件：

    tests/test_get_positions.py

如果文件已存在且希望在文件末尾追加一个新的测试函数，可以加上 --append。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import textwrap


REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = REPO_ROOT / "tests"


def snake_to_camel(s: str) -> str:
  parts = [p for p in s.replace("-", "_").split("_") if p]
  return "".join(part.capitalize() for part in parts)


def guess_feature(marker: str) -> str:
  mapping = {
      "order": "订单",
      "position": "仓位",
      "error": "错误",
      "smoke": "冒烟",
      "concurrent": "并发",
  }
  return mapping.get(marker, "通用")


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="根据接口名称生成 pytest 测试骨架")
  parser.add_argument(
      "--name",
      required=True,
      help="接口/场景名称（例如 place_order、get_positions），用于生成文件名和函数名",
  )
  parser.add_argument(
      "--marker",
      required=True,
      help="pytest 标记，例如：smoke/order/position/error/concurrent",
  )
  parser.add_argument(
      "--feature",
      help="Allure feature；未提供时会根据 marker 自动推断（如 position -> 仓位）",
  )
  parser.add_argument(
      "--story",
      help="Allure story；未提供时默认等于 name",
  )
  parser.add_argument(
      "--title",
      help="用例标题；未提供时默认 '<name> works correctly'",
  )
  parser.add_argument(
      "--append",
      action="store_true",
      help="如果目标文件已存在，则在文件末尾追加一个新的测试函数，而不是报错退出",
  )
  return parser.parse_args()


def ensure_tests_dir() -> None:
  if not TESTS_DIR.exists():
      TESTS_DIR.mkdir(parents=True, exist_ok=True)


def create_new_file(
    file_path: Path,
    name: str,
    marker: str,
    feature: str,
    story: str,
    title: str,
) -> None:
  """在 tests/ 下创建一个新的测试文件。"""
  class_name = f"Test{snake_to_camel(name)}"

  template = textwrap.dedent(
      f'''
      import allure
      import pytest

      from client.hyperliquid_client import HyperliquidClient


      @allure.feature("{feature}")
      @allure.story("{story}")
      @pytest.mark.{marker}
      class {class_name}:
          @allure.title("{title}")
          def test_{name}(self, client: HyperliquidClient, default_coin: str):
              # TODO: 调用 client.{name}(...) 并补充断言
              # 示例：
              # resp = client.{name}(...)
              # assert resp is not None
              raise NotImplementedError("请补充具体断言")
      '''
  ).lstrip()

  file_path.write_text(template, encoding="utf-8")
  print(f"[new_test_case] 已创建文件: {file_path}")


def append_test_function(
    file_path: Path,
    name: str,
    marker: str,
    title: str,
) -> None:
  """在已有测试文件末尾追加一个测试函数。"""
  snippet = textwrap.dedent(
      f'''


      @allure.title("{title}")
      @pytest.mark.{marker}
      def test_{name}(client: HyperliquidClient, default_coin: str):
          # TODO: 调用 client.{name}(...) 并补充断言
          raise NotImplementedError("请补充具体断言")
      '''
  )

  # 确保文件开头有基础 import（若是旧文件可能没有）
  original = file_path.read_text(encoding="utf-8")
  needs_imports = "import pytest" not in original or "import allure" not in original
  if needs_imports:
      header = "import allure\nimport pytest\n\nfrom client.hyperliquid_client import HyperliquidClient\n\n"
      new_content = header + original.rstrip() + snippet
  else:
      new_content = original.rstrip() + snippet

  file_path.write_text(new_content, encoding="utf-8")
  print(f"[new_test_case] 已在文件末尾追加用例: {file_path}")


def main() -> int:
  args = parse_args()
  name = args.name.strip()
  marker = args.marker.strip()

  if not name.isidentifier() and "-" in name:
      # 允许用连字符，但要提示
      print(f"[new_test_case] 提示: --name 中包含 '-'，将自动按 '_' 处理。", file=sys.stderr)
      name = name.replace("-", "_")

  feature = (args.feature or guess_feature(marker)).strip()
  story = (args.story or name).strip()
  title = (args.title or f"{name} works correctly").strip()

  ensure_tests_dir()
  file_path = TESTS_DIR / f"test_{name}.py"

  if file_path.exists() and not args.append:
      print(f"[new_test_case] 文件已存在: {file_path}", file=sys.stderr)
      print("[new_test_case] 如需在该文件中追加用例，请增加 --append 参数。", file=sys.stderr)
      return 1

  if not file_path.exists():
      create_new_file(file_path, name, marker, feature, story, title)
  else:
      append_test_function(file_path, name, marker, title)

  return 0


if __name__ == "__main__":
  raise SystemExit(main())

