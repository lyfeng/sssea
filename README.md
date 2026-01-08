# SSSEA Agent - 技术文档

**Sentient Security Sandbox Execution Agent**

基于 ROMA 框架的 Web3 安全审计智能体，为 Sentient GRID 网络提供意图对齐审计服务。

---

## 项目概述

SSSEA 是一个**基于 ROMA 框架的自主型安全代理 (Autonomous Security Agent)**，采用递归推理方式进行交易安全分析：

1. **接收 Agent 请求**：通过 OpenAI 兼容接口接收 `[用户意图 + 交易数据]`
2. **ROMA 递归分析**：使用 Perception → Planner → Executor → Reflection → Aggregator 流程
3. **TEE 沙盒模拟**：在 Anvil 分叉环境中执行交易模拟
4. **意图对齐审计**：通过递归推理判断交易结果是否符合用户意图
5. **返回 OML 证明**：输出带硬件签名的安全报告

### ROMA 框架集成

SSSEA 基于 [ROMA (Recursive Open Meta-Agent)](https://github.com/sentient-agi/ROMA) 框架构建：

- **Perception Agent**: 解析用户意图和交易数据
- **Planner Agent**: 将复杂任务分解为子任务
- **Executor Agent**: 调用工具执行子任务
- **Reflection Agent**: 分析结果并决定是否重试
- **Aggregator Agent**: 聚合结果生成最终报告

---

## 快速开始

### 1. 环境要求

- Python 3.12+
- Foundry/Anvil（用于主网分叉模拟）
- 可选：AWS Nitro Enclaves（生产环境）

### 2. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -e .
```

### 3. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 主要配置项：
# - ROMA_API_KEY: LLM API Key (推荐使用 OpenRouter)
# - MAINNET_RPC_URL: 以太坊主网 RPC
```

### 4. 启动服务

```bash
# 开发模式
python src/main.py

# 或使用 uvicorn
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 运行 E2E Demo

```bash
python scripts/demo_client.py
```

---

## 项目结构

```
sssea/
├── config/                    # ROMA 配置文件
│   ├── profiles/             # 环境配置 (dev.yaml, prod.yaml)
│   └── roma_config.py        # 配置加载器
├── src/
│   ├── main.py               # FastAPI 主入口
│   ├── config.py             # 配置管理
│   ├── agents/               # ROMA Agent 组件
│   │   ├── base.py           # Agent 基类
│   │   ├── perception.py     # 感知层 Agent
│   │   ├── planner.py        # 规划层 Agent
│   │   ├── executor.py       # 执行层 Agent
│   │   ├── reflection.py     # 反思层 Agent
│   │   ├── aggregator.py     # 聚合层 Agent
│   │   └── pipeline.py       # ROMA Pipeline
│   ├── toolkits/             # ROMA Toolkits
│   │   ├── base.py           # Toolkit 基类
│   │   ├── anvil_toolkit.py  # EVM 模拟工具
│   │   ├── tee_toolkit.py    # TEE 管理工具
│   │   └── forensics_toolkit.py  # 取证分析工具
│   ├── simulation/           # 模拟引擎层
│   │   ├── models.py         # 数据模型
│   │   └── anvil_screener.py # Anvil 模拟引擎
│   ├── attestation/          # OML 证明层
│   │   └── mock_quote.py     # Mock 证明生成器
│   └── api/                  # API 层
│       └── openai_compat.py  # OpenAI 兼容接口
├── scripts/
│   ├── check_env.py          # 环境检查脚本
│   └── demo_client.py        # E2E Demo 客户端
├── tests/                    # 单元测试
├── .env.example              # 环境变量模板
├── pyproject.toml            # 项目配置
└── README.md                 # 本文档
```

---

## ROMA Pipeline 执行流程

SSSEA 使用 ROMA 框架的递归推理流程：

```
┌─────────────┐
│  Perception │ ← 解析用户意图和交易数据
└──────┬──────┘
       │
       ├─────────────┐
       │             │
       ▼             ▼
┌─────────────┐ ┌─────────┐
│   Planner   │ │ 简单任务 │ ← 复杂任务需要 Planner 分解
└──────┬──────┘ └────┬────┘
       │             │
       └──────┬──────┘
              ▼
      ┌─────────────┐
      │  Executor   │ ← 调用 Toolkits 执行模拟和分析
      └──────┬──────┘
             │
             ▼
      ┌─────────────┐
      │ Reflection  │ ← 分析结果，决定是否重试
      └──────┬──────┘
             │
             ▼
      ┌─────────────┐
      │ Aggregator  │ ← 聚合结果，生成最终报告
      └─────────────┘
```

### Toolkits

ROMA Pipeline 可调用的工具集：

| Toolkit | 功能 | 主要方法 |
|---------|------|----------|
| `anvil_simulator` | EVM 交易模拟 | `simulate_tx`, `get_balance`, `get_code` |
| `tee_manager` | TEE 管理 | `create_enclave`, `generate_key`, `get_attestation` |
| `forensics_analyzer` | 取证分析 | `analyze_trace`, `detect_attack`, `check_risk_patterns` |

---

## API 接口

### OpenAI 兼容接口

**端点**: `POST /v1/chat/completions`

**请求示例**:
```json
{
  "model": "sssea-v1-roma",
  "messages": [
    {"role": "user", "content": "请审计以下交易"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "simulate_tx",
        "arguments": {
          "user_intent": "Swap 1 ETH to USDC",
          "tx_from": "0x...",
          "tx_to": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
          "tx_value": "1000000000000000000"
        }
      }
    }
  ]
}
```

**响应示例**:
```json
{
  "id": "chatcmpl-xxx",
  "choices": [...],
  "system_fingerprint": "sssea-roma@dev_xxx",
  "metadata": {
    "oml_attestation": "eyJ2ZXJzaW9uIjogIk9NTF8xLjAi...",
    "risk_level": "SAFE",
    "risk_score": 85,
    "pipeline_used": true,
    "execution_steps": ["perception", "executor", "reflection", "aggregator"]
  }
}
```

### 简化模拟接口

**端点**: `POST /api/v1/simulate`

---

## 配置

### ROMA 配置文件

配置文件位于 `config/profiles/` 目录：

- **dev.yaml**: 开发环境配置（Mock模式，单线程执行）
- **prod.yaml**: 生产环境配置（完整ROMA流程，并行执行）

### 关键配置项

```yaml
# ROMA Pipeline
pipeline:
  enabled_agents: [perception, planner, executor, reflection, aggregator]
  max_retries: 3
  timeout: 600

# ROMA 组件
roma:
  enabled: true
  model: "openai/gpt-4o"
  provider: "openrouter"

# Toolkits
toolkits:
  anvil_simulator:
    fork_url: "https://eth.llamarpc.com"
    timeout: 30
  tee_manager:
    backend: "docker-sim"  # 或 "nitro"
  forensics_analyzer:
    enable_ml_detection: true
```

---

## 核心组件

### ROMA Pipeline

**文件**: `src/agents/pipeline.py`

完整的 Agent 执行流程，协调各个 Agent 的调用。

```python
from src.agents import SSSEAPipeline

pipeline = SSSEAPipeline(config)
result = await pipeline.run(
    user_intent="Swap 1 ETH to USDC",
    tx_data={
        "tx_from": "0x...",
        "tx_to": "0x...",
        "tx_value": "1000000000000000000"
    }
)
```

### Toolkits

**文件**: `src/toolkits/`

所有 Toolkit 继承自 `BaseToolkit`，实现统一的接口：

```python
from src.toolkits import AnvilToolkit, TEEToolkit, ForensicsToolkit

anvil = AnvilToolkit(config={"fork_url": "..."})
result = await anvil(action="simulate_tx", user_intent="...", ...)
```

### 数据模型

**文件**: `src/simulation/models.py`

- `SimulationRequest`: 模拟请求
- `SimulationResult`: 模拟结果
- `RiskLevel`: 风险等级 (SAFE/WARNING/CRITICAL)

---

## 测试

### 运行单元测试

```bash
# 所有测试
pytest

# 特定模块
pytest tests/test_agents.py
pytest tests/test_toolkits.py
```

### 环境检查

```bash
python scripts/check_env.py
```

---

## Agent 协作流程

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   User      │─────▶│ Swap Agent  │─────▶│   SSSEA     │
│             │      │             │      │  (ROMA)     │
└─────────────┘      └─────────────┘      └─────────────┘
                            │                      │
                            ▼                      ▼
                      构建 Tx              ROMA Pipeline 分析
                            │                      │
                            ◀──────────────────────┘
                            │
                     返回安全报告
                            │
                            ▼
┌─────────────┐      ┌─────────────┐
│   User      │◀─────│ Swap Agent  │
│  (确认执行)  │      │             │
└─────────────┘      └─────────────┘
```

---

## ROMA 框架

SSSEA 基于 [ROMA (Recursive Open Meta-Agent)](https://github.com/sentient-agi/ROMA) 框架构建。

ROMA 是一个开源的元智能体框架，支持：
- **递归推理**: Agent 可以递归地分解和解决复杂任务
- **工具调用**: 通过 Toolkit 接口调用外部工具
- **验证机制**: Verifier 组件验证输出质量
- **可观测性**: MLflow 集成用于实验跟踪

### 参考

- [ROMA GitHub](https://github.com/sentient-agi/ROMA)
- [ROMA 文档](https://sentient-agi.github.io/ROMA/)
- [Sentient Blog](https://blog.sentient.xyz/)

---

## 下一步

1. **真实 Anvil 集成**：替换 Mock 模拟为真实的主网分叉
2. **LLM 集成**：接入真实 OpenAI/Claude API
3. **TEE 部署**：打包为 AWS Nitro Enclaves EIF
4. **OML 注册**：在 Sentient Spark 阶段注册 Agent

---

## 许可证

MIT License
