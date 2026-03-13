# 🚀 Hyperliquid 自动化测试框架

> 专为 **Hyperliquid Testnet API** 打造的自动化测试方案 · 自研 Client · 一键 CI · 报告自动发布

针对 Hyperliquid Testnet 的账户、订单、仓位等核心能力做持续回归，自动生成 Allure 报告并发布到 Cloudflare Pages，开箱即用。

---

## ✨ 为什么选这个框架？


| 特性                           | 说明                                                                                        |
| ---------------------------- | ----------------------------------------------------------------------------------------- |
| 🔧 **自研 Hyperliquid Client** | 不依赖官方/社区 SDK，完整实现请求封装 + EIP‑712 phantom‑agent 签名                                          |
| ⚡ **一键 CI & 报告**             | GitHub Actions 跑测试 → 生成 Allure 报告 → 自动部署到 Cloudflare Pages，固定域名随时查看                       |
| 🛡️ **安全的测试网回放**             | 默认连 Testnet，读写分离、只对读操作重试，写操作不重试，避免重复下单                                                    |
| 🧹 **良好的测试隔离**               | Session 开始/每个用例后/Session 结束都会清理**未成交单**（open orders），跑完 pytest 后 open 订单数应为 0；历史订单数会随测试增加 |


---

## 🏃 快速开始

### 场景一：GitHub Actions 在线执行

在仓库 **Settings → Secrets and variables → Actions** 中配置：

- **Secrets**（敏感信息，需加密存储）  
  - `HL_WALLET_ADDRESS`：测试网钱包地址  
  - `HL_PRIVATE_KEY`：对应私钥（务必使用测试钱包）  
  - `CF_ACCOUNT_ID` / `CF_API_TOKEN` / `CF_PAGES_PROJECT_NAME`：Cloudflare Pages 部署所需
- **Variables**（非敏感配置）  
  - `DAILY_SCHEDULE_ENABLED`（可选）：设为 `true` 时启用每天北京时间 00:00 定时测试；不设或非 `true` 时仅手动触发

配置完成后，在 **Actions** 页面选择工作流并点击 **Run workflow** 即可执行；报告会自动部署到 Cloudflare Pages（见下文「Allure 报告」）。

---

### 场景二：本地开发执行

**1. 环境与依赖**

- Python ≥ 3.10、pip
- 安装依赖：

```bash
cd hyperliquid-test-framework
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**2. 配置**

```bash
cp .env.example .env
# 编辑 .env，填入 HL_WALLET_ADDRESS 和 HL_PRIVATE_KEY
```

> ⚠️ **安全提示**：`.env` 已在 `.gitignore` 中，绝不要把私钥提交到仓库。

**3. 运行测试**

```bash
# 运行全部测试
pytest

# 只运行 smoke 测试（快速、不具有破坏性）
pytest -m smoke

# 按模块运行
pytest -m order       # 订单
pytest -m position    # 仓位
pytest -m error       # 错误处理
pytest -m concurrent  # 并发（可选）
```

**4. 快速生成新测试用例骨架**

```bash
python scripts/new_test_case.py \
  --name get_positions \
  --marker position \
  --feature "仓位" \
  --story "查询仓位" \
  --title "查询仓位列表结构正确"
```

会在 `tests/` 下生成 `test_get_positions.py`，包含带 Allure 标注和 `@pytest.mark.position` 的用例骨架，按需补充调用和断言即可。若文件已存在，可加 `--append` 在文件末尾追加新用例。

---

## 📊 Allure 报告 & Cloudflare Pages

- 测试结果以 Allure 原始数据写入 `reports/allure-results`，**每次运行前会清空目录，只保留本次结果**。
- CI 中会自动：
  1. 运行 smoke + 全量测试
  2. 用 `allure generate` 生成 `reports/allure-report`（静态 HTML）
  3. 通过 Cloudflare Pages Action 部署到你配置的 Pages 项目
  4. 在 GitHub Actions 的 Job 摘要中写入报告链接（例如 `https://report.hioo.de/`）

**本地查看**（已安装 Allure CLI 时）：

```bash
pytest
allure serve reports/allure-results          # 启动本地服务查看
# 或
allure generate reports/allure-results -o reports/allure-report --clean
allure open reports/allure-report
```

---

## 🔄 CI 工作流概览

- **工作流文件**：`.github/workflows/Hyperliquid_test_suite.yml`
- **触发方式**：
  - **手动触发**：在 GitHub Actions 页面点击 “Run workflow”，可通过 `marker` 输入控制本次运行范围：
    - 为空：跑默认组合（smoke + 全量，排除 concurrent）
    - `smoke` / `order` / `position` / `error` / `concurrent`：等同执行 `pytest -m <marker> -v`
  - **定时触发（可选）**：每天北京时间 00:00，是否执行由仓库 Variable `DAILY_SCHEDULE_ENABLED` 控制  
    - 未设置或值 ≠ `true`：仅手动触发会跑  
    - 设为 `true`：手动 + 每天定时都会跑

---

## 📁 项目结构（精简版）

```
client/         # 自研 Hyperliquid API Client（请求封装 + 签名）
models/         # 账户 / 订单 / 仓位等 Pydantic 模型
tests/          # 测试用例：account / orders / positions / errors / concurrent
fixtures/       # pytest fixtures（客户端生命周期、默认合约等）
support/        # config / logger / retry / waiters 等测试基础设施
.github/        # GitHub Actions 工作流
reports/        # Allure 结果与 HTML 报告输出目录
```

---

## ⚠️ 已知限制

- 依赖 Testnet 流动性，IOC 订单偶尔可能无法成交，对应用例会 skip。
- 并发测试受 rate limit 影响，成功率阈值设置为 60%。
- 签名逻辑基于当前协议实现，如 Hyperliquid 调整签名协议，需要同步更新本项目实现。

