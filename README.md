# Hyperliquid Automated Testing Framework

针对 **Hyperliquid Testnet API** 设计的自动化测试框架，覆盖账户查询、订单生命周期、仓位管理和错误处理等核心场景。

---

## 快速开始

### 1. 环境要求

- Python ≥ 3.10
- pip

### 2. 安装依赖

```bash
cd hyperliquid-test-framework
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 配置

- **仅通过 GitHub Actions 跑测试**：在仓库 **Settings → Secrets and variables → Actions** 中配置 `HL_WALLET_ADDRESS`、`HL_PRIVATE_KEY` 等（见下方 CI 与 Allure 报告一节），无需本地 `.env`。
- **要在本地运行测试**：复制环境变量模板并填入测试钱包信息：
  ```bash
  cp .env.example .env
  # 编辑 .env，填入 HL_WALLET_ADDRESS 和 HL_PRIVATE_KEY
  ```
  > **安全提示**：`.env` 已在 `.gitignore` 中，绝不要将私钥提交到代码仓库。

### 4. 运行测试

```bash
# 运行全部测试
pytest

# 只运行 smoke 测试（快速验证，无破坏性操作）
pytest -m smoke

# 只运行订单测试
pytest -m order

# 只运行仓位测试
pytest -m position

# 只运行错误处理测试
pytest -m error

# 运行并发测试（可选）
pytest -m concurrent

# 生成 Allure 报告（需先安装 Allure CLI，见下方）
pytest
allure generate reports/allure-results -o reports/allure-report --clean
allure open reports/allure-report
# 或一键：./scripts/allure_report.sh（先 pytest 再生成 Allure HTML 并打开）
# 或临时服务：allure serve reports/allure-results
```

---

## Allure 报告与 Cloudflare Pages

本框架默认将 Allure 原始结果写入 `reports/allure-results`（见 `pyproject.toml`），**每次运行 pytest 前会清空该目录**，报告只包含本次运行结果。

- **内容**：环境信息、Feature/Story 分组（账户、订单、仓位、错误处理、并发）、每次 API 调用的请求/响应附件。

### 本地查看 Allure 报告

- **安装 Allure CLI**：
  - macOS：`brew install allure`
  - 其他平台：参考官方文档 `https://github.com/allure-framework/allure2/releases`
- **查看报告**：
  - 已有 `allure-results` 时：
    ```bash
    allure serve reports/allure-results
    ```
  - 或生成静态 HTML 后手动打开：
    ```bash
    pytest
    allure generate reports/allure-results -o reports/allure-report --clean
    allure open reports/allure-report
    ```

### 使用 GitHub Actions + Cloudflare Pages 自动发布报告

本仓库已内置 CI 工作流 `.github/workflows/Hyperliquid_test_suite.yml`，支持 **自动在云端生成 Allure HTML 并发布到 Cloudflare Pages**。你只需配置好 Secrets，fork 后即可一键跑通。

- **Hyperliquid 钱包相关 Secrets（用于真实下单）**：
  - `HL_WALLET_ADDRESS`：测试网钱包地址
  - `HL_PRIVATE_KEY`：对应私钥（仅用于 CI，务必使用测试钱包）

- **Cloudflare Pages 相关 Secrets（用于发布 HTML 报告）**：
  - `CF_ACCOUNT_ID`：Cloudflare 账号 ID
  - `CF_API_TOKEN`：具有 Pages 写入权限的 API Token
  - `CF_PAGES_PROJECT_NAME`：Cloudflare Pages 项目名（例如 `hyperliquid-allure`）

在 GitHub 仓库中依次创建：

```text
Settings → Secrets and variables → Actions → New repository secret
  - HL_WALLET_ADDRESS
  - HL_PRIVATE_KEY
  - CF_ACCOUNT_ID
  - CF_API_TOKEN
  - CF_PAGES_PROJECT_NAME
```

完成上述配置后：

- 手动触发或定时触发 **Hyperliquid Test Suite** 时：
  - CI 会在 Ubuntu Runner 上安装 Allure CLI；
  - 运行 smoke / 全量测试，生成 `reports/allure-results`；
  - 使用 `allure generate` 生成 `reports/allure-report`（静态 HTML）；
  - 通过 Cloudflare Pages Action 将该目录发布到你的 Pages 项目。
- 最终你可以在 Cloudflare Pages 配置的域名（例如 `https://allure.your-domain.com`）上直接查看最新一轮 CI 的 Allure 报告。

---

## 项目结构

```
hyperliquid-test-framework/
│
├── client/                        # API Client 层
│   ├── hyperliquid_client.py      # 核心 client：账户、订单、仓位、市场数据
│   ├── signer.py                  # EIP-712 签名（phantom-agent 流程）
│   └── exceptions.py              # 统一异常层级
│
├── models/                        # Pydantic 数据模型
│   ├── account.py                 # 账户 / clearinghouse 状态
│   ├── order.py                   # 订单相关模型
│   └── position.py                # 仓位模型
│
├── tests/                         # 测试用例
│   ├── test_account.py            # 账户信息 & 元数据测试
│   ├── test_orders.py             # 订单生命周期测试
│   ├── test_positions.py          # 仓位开仓/平仓测试
│   ├── test_errors.py             # 错误处理测试
│   └── test_concurrent.py         # 并发测试（可选）
│
├── fixtures/                      # pytest fixtures
│   └── wallet_fixture.py          # 客户端生命周期 & 测试隔离
│
├── support/                       # 测试基础设施
│   ├── config.py                  # 配置管理（env + yaml）
│   ├── logger.py                  # 结构化日志 + 脱敏
│   ├── retry.py                   # 可配置重试装饰器
│   ├── waiters.py                 # 轮询等待工具
│   └── ids.py                     # 唯一标识生成
│
├── config/
│   └── config.yaml                # 默认配置
│
├── .github/workflows/
│   └── Hyperliquid_test_suite.yml  # GitHub Actions CI（仅定时 + 手动触发，不随 push/PR 跑）
│
├── reports/                       # 测试报告输出目录
├── conftest.py                    # pytest 根 conftest
├── pyproject.toml                 # 项目 & pytest 配置
├── requirements.txt               # Python 依赖
├── .env.example                   # 环境变量模板
├── .gitignore
└── README.md
```

---

## 框架设计

### 分层架构

```
Tests  →  Fixtures  →  Client  →  Signer
  ↕           ↕          ↕          ↕
Support (config, retry, waiters, logger, ids)
```

- **Client 层**：自研 API Client，不依赖任何官方/社区 SDK。封装了 HTTP 请求、EIP-712 签名、统一错误处理。
- **Signer 层**：实现 Hyperliquid L1 action 的 phantom-agent 签名流程（msgpack → keccak256 → EIP-712 typed data signing）。
- **Support 层**：可复用的测试基础设施，包含配置管理、重试装饰器、轮询等待、日志脱敏、唯一 ID 生成等。
- **Fixtures 层**：管理测试客户端的生命周期，并在每个测试结束后自动清理未成交订单，保证测试隔离。

### 关键设计决策

| 决策点 | 方案 | 理由 |
|--------|------|------|
| HTTP 客户端 | httpx | 同步/异步双模、超时控制好 |
| 签名 | 自实现 (eth-account + msgpack) | 禁用官方 SDK 的约束 |
| 重试 | 仅对读操作重试 | 避免写操作重复执行 |
| 等待机制 | 轮询 + 超时 | 适配 testnet 最终一致性 |
| 测试隔离 | 每测试后清理所有 open orders | 避免测试之间互相污染 |
| 配置 | env vars > config.yaml | 本地 .env 开发，CI 用 secrets |
| 日志 | 自动脱敏私钥/签名 | 防止敏感信息泄漏 |

### 重试策略

- **读操作** (`_post_info`)：自动重试 3 次，指数退避（1s → 2s → 4s）
- **写操作** (`_post_exchange`)：**不自动重试**，避免重复下单
- 应用层可通过 `@retry` 装饰器自定义策略

### 等待机制

使用 `wait_until()` 轮询器处理 testnet 延迟：

```python
from support.waiters import wait_until

order = wait_until(
    lambda: client.get_order_status(oid).get("order"),
    description="order becomes visible",
    timeout=30,
    interval=1.0,
)
```

---

## 测试覆盖说明

### Account Tests (`test_account.py`)
- 账户信息字段结构验证
- marginSummary / crossMarginSummary 完整性
- 账户余额非负
- 元数据 (universe) 结构
- 中间价查询

### Order Lifecycle Tests (`test_orders.py`)
- 创建限价买/卖单
- 带 cloid 下单
- 查询 open orders 包含新订单
- 查询订单状态为 open
- 按 oid 撤单
- 按 cloid 撤单
- 重复撤单返回错误
- 撤单后状态变为 canceled

### Position Tests (`test_positions.py`)
- 开多仓后仓位可查
- 验证 position size > 0
- 验证 entry price 合理
- 平仓后仓位归零
- 仓位字段结构验证

### Error Handling Tests (`test_errors.py`)
- 非法 symbol 拒绝
- 零价格 / 负价格拒绝
- 零数量 / 低于最小 notional 拒绝
- 取消不存在的订单
- reduce-only 无仓位时的行为

### Concurrent Tests (`test_concurrent.py`)（可选）
- 同时提交 5 个订单
- 验证成功率 ≥ 60%

---

## CI

项目配置了 GitHub Actions（`.github/workflows/Hyperliquid_test_suite.yml`），**仅在手动触发或定时触发时运行**（不随 push/PR 自动跑，节省 token）：

1. **Smoke 测试**：`tests/test_account.py` + `tests/test_errors.py`，标记为 `smoke or error`，即使钱包未配置也会尝试运行。
2. **完整测试**：当仓库 Secrets 中存在 `HL_PRIVATE_KEY` 时，会运行除并发测试外的全部用例（`-m "not concurrent"`）。
3. **Allure 报告**：
   - 所有运行都会把 `reports/` 目录（含 `allure-results`）上传为 GitHub Actions artifact；
   - 当配置了 Cloudflare 相关 Secrets 且 Python 版本为 3.12 的那条流水线，会自动生成并发布 Allure HTML 到 Cloudflare Pages。

### 每日定时执行（可选）

工作流支持 **按北京时间每天 00:00 自动跑一轮测试**，由 **仓库变量** **`DAILY_SCHEDULE_ENABLED`** 控制（因 job 级 `if` 中不能使用 `env`，故用变量）：

| 配置 | 含义 |
|------|------|
| 未设置或 ≠ `true` | 不执行定时任务：只有手动触发时会跑。 |
| 设为 `true` | 开启定时：除上述触发外，每天北京时间 0 点会再自动跑一次。 |

**开启方式**：在 GitHub 仓库 **Settings → Secrets and variables → Actions → Variables** 中，新增变量名 `DAILY_SCHEDULE_ENABLED`，值填 `true`。关闭则删除该变量或将值改为非 `true`。定时使用 GitHub `schedule`（cron），当前配置对应北京 00:00。

> 推荐在 fork 后，先只配置 `HL_WALLET_ADDRESS` 和 `HL_PRIVATE_KEY` 验证测试，再补充 Cloudflare 的 3 个 Secrets，最后在 Cloudflare Pages 里为项目绑定你自己的域名，以便通过固定 URL 访问最新报告。

---

## 已知限制

- Testnet 可能存在流动性不足，导致 IOC 订单无法成交，部分仓位测试会 skip
- 共享测试钱包场景下，测试之间可能存在互相影响
- 并发测试在 testnet 受 rate limit 影响，成功率阈值设为 60%
- 签名实现基于对 Python SDK 签名流程的逆向理解，如果 Hyperliquid 更新签名协议需要同步调整
