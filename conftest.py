"""根 conftest：把项目根加入 sys.path，并导出 wallet_fixture 中的 session fixtures。"""

import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fixtures.wallet_fixture import *  # noqa: F401, F403, E402


def pytest_configure(config):
    """每次运行前清空 reports/allure-results，再创建目录并写入 environment.properties。"""
    allure_results = Path("reports/allure-results")
    if allure_results.exists():
        shutil.rmtree(allure_results)
    allure_results.mkdir(parents=True, exist_ok=True)
    env_file = allure_results / "environment.properties"
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(f"Python={sys.version.split()[0]}\n")
        f.write(f"Base.URL={os.getenv('HL_BASE_URL', 'https://api.hyperliquid-testnet.xyz')}\n")
        f.write(f"Mainnet={os.getenv('HL_IS_MAINNET', 'false')}\n")
        f.write(f"Default.Coin={os.getenv('HL_DEFAULT_COIN', 'ETH')}\n")
