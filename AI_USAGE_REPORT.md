# AI 使用报告

## 1. 使用的 AI 工具及模型

| 工具 | 模型 | 用途 |
|------|------|------|
| Cursor IDE (Claude) | Claude Opus | 需求分析、架构设计、代码生成、文档编写 |

## 2. 关键 Prompts 示例

### 需求分析阶段

```
帮我以开发者角度分析一下当前打开的需求文档
```
→ AI 从开发视角识别了文档中的歧义点、风险项和需要补充设计的部分。

### 架构设计阶段

```
根据开发计划开始为我从 0 到 1 搭建
```
→ AI 先调研了 Hyperliquid API 文档（info endpoint、exchange endpoint、签名机制），
然后参考官方 Python SDK 的签名逻辑（非直接使用）设计了自研 client 的实现方案。

### API 调研

AI 自动抓取并阅读了以下文档：
- Hyperliquid exchange endpoint 文档
- Hyperliquid info endpoint 文档
- Nonces and API wallets 文档
- Perpetuals metadata 文档
- 官方 Python SDK 的 signing.py 源码（用于理解签名流程，未直接使用）

## 3. AI 生成代码比例（估计）

| 模块 | AI 生成比例 | 说明 |
|------|------------|------|
| 项目结构 & 配置 | ~90% | 目录结构、pyproject.toml、requirements.txt 等 |
| Client / Signer | ~85% | 签名流程参考 SDK 源码后由 AI 重新实现 |
| 测试基础设施 | ~90% | retry、waiters、logger、config 等 |
| 测试用例 | ~80% | 测试场景由 AI 根据需求文档设计 |
| CI 配置 | ~95% | GitHub Actions workflow |
| 文档 | ~70% | README 框架由 AI 生成，需人工审校 |

**整体估计：AI 生成约 85%，人工审校和调整约 15%。**

## 4. AI 帮助解决的问题

1. **签名机制理解**：AI 阅读了官方 SDK 的 signing.py 源码，提取出 phantom-agent 签名的完整流程（msgpack 序列化 → keccak256 哈希 → EIP-712 typed data → 签名），并用 eth-account 库重新实现。

2. **API 接口梳理**：AI 从 Hyperliquid 的 GitBook 文档中提取了所有需要用到的 endpoint、请求格式和响应结构，省去了大量手动阅读文档的时间。

3. **测试设计**：AI 根据需求文档中的测试场景描述，设计了具体的测试用例，包括边界条件、等待策略和清理逻辑。

4. **工程实践**：日志脱敏、测试隔离、读写操作差异化重试策略等工程能力均由 AI 主动建议并实现。

## 5. AI 无法解决的问题

1. **Testnet 实际行为验证**：AI 无法实际运行测试来验证 testnet 的真实行为（如延迟、rate limit、最小下单量的具体表现）。需要人工运行测试并根据实际表现调整参数。

2. **签名正确性验证**：虽然 AI 参照 SDK 实现了签名逻辑，但无法保证在 testnet 上的签名一定被接受。需要人工运行验证并调试。

3. **Testnet 流动性判断**：AI 无法预知 testnet 的实时流动性状况，仓位测试中的 IOC 单能否成交取决于当时的 orderbook 深度。

4. **共享钱包冲突**：多人共用同一测试钱包时的竞态条件和数据污染问题，需要在实际运行中观察并调整测试策略。

5. **性能调优**：并发测试的参数（并发数、超时、成功率阈值）需要根据实际运行结果进行调整，AI 给出的是合理默认值。
