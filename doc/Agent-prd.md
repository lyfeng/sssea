这份文档是为您量身定制的 **SSSEA Agent (Phase 1)** 完整需求文档。它将之前的“工具”逻辑全面升级为“**自主智能体（Autonomous Agent）**”逻辑，旨在直接满足 **Sentient Builder Program** 的评审标准。

---

# 📄 产品需求文档 (PRD): SSSEA Security Copilot Agent

**项目名称：** Sentient Security Sandbox Execution Agent (SSSEA)

**定位：** 基于 TEE 的自主 Web3 安全审计智能体

**版本：** v1.0 (Phase 1 - Web3 Focus)

**日期：** 2026-01-07

---

## 1. 产品愿景与目标 (Vision & Goals)

### 1.1 产品愿景

打造 Web3 AGI 时代的“安全大脑”。SSSEA 不仅是一个模拟器，它是一个能够理解人类意图、自主拆解复杂合约逻辑、并在隔离环境中执行风险博弈的 **Security Copilot Agent**。

### 1.2 核心目标 (MVP)

1. **意图对齐 (Intent Alignment)：** 利用 LLM 推理，判断链上交互是否偏离用户初衷。
2. **确定性模拟 (Deterministic Simulation)：** 在 TEE + Foundry 环境下实现 100% 还原的执行回测。
3. **可证实的合规 (Verifiable Compliance)：** 通过 OML 1.0 协议输出带硬件签名的安全证明。

---

## 2. 智能体架构与逻辑流 (Agentic Architecture)

不同于传统 API，SSSEA 运行一个 **感知-推理-动作 (Perception-Reasoning-Action)** 的闭环。

### 2.1 递归推理工作流 (ROMA Workflow)

1. **感知 (Perception)：** 接收用户自然语言意图及交易 Data。
2. **分解 (Planning)：** Agent 将任务拆解为：(a) 意图语义分析；(b) 环境分叉准备；(c) 模拟执行；(d) 风险溯源。
3. **执行 (Action)：** 动态拉起 TEE 沙盒，注入临时密钥，运行 Anvil 模拟。
4. **反思 (Reflection)：** 若模拟结果异常（如交易回滚），Agent 会尝试自动调整状态覆盖（State Override）以寻找失败原因，判断是“技术 Bug”还是“恶意欺诈”。

---

## 3. 功能需求 (Functional Requirements)

### 3.1 意图感知层 (Intent Perception)

* **FR-01 自然语言理解：** 能够解析类似“我想以不高于 1% 的滑点在 Uniswap 换取 10 ETH”的指令。
* **FR-02 意图冲突检测：** 如果模拟执行显示资金流向了非官方合约或滑点设为 100%，Agent 必须主动识别为“意图不匹配”。

### 3.2 自主执行层 (Autonomous Execution)

* **FR-03 TEE 动态沙盒：** 自动化管理 AWS Nitro Enclaves 的生命周期。
* **FR-04 主网分叉模拟：** 集成 Foundry/Anvil，支持实时同步链上状态进行 0-Gas 模拟。
* **FR-05 资产流向解析：** 自动追踪并分类所有 ERC-20, ERC-721, ERC-1155 的余额变动。

### 3.3 Sentient 协议集成 (OML Protocol)

* **FR-06 远程度量 (Attestation)：** 每次输出必须附带由 TEE 签署的 PCR0 哈希证明。
* **FR-07 OML 结算接口：** 适配 Sentient 账单逻辑，根据模拟的价值和风险等级自动计算服务费。

---

## 4. 技术规范 (Technical Specifications)

### 4.1 OpenAI 兼容接口规范

SSSEA 必须支持以 `Chat Completion` 的形式被调用，以便其他 Agent 协作。

* **Endpoint:** `POST /v1/chat/completions`
* **关键 Payload 定义：**
* `tools`: 定义 `simulate_tx` 函数。
* `system_fingerprint`: 映射为 TEE 硬件指纹。
* `metadata`: 存储 `oml_quote` 和资产变动快照。



### 4.2 数据库结构 (Core Schema)

* **`agent_memories`**: 存储用户的历史偏好（如常用的白名单地址）。
* **`simulation_traces`**: 存储脱敏后的模拟执行路径，用于后续的风险特征学习。
* **`attestation_vault`**: 存储与任务关联的硬件签名原始数据。

### 4.3 行为异常检测模块 (Anomaly Detection Module)

* **Requirement ID:** FR-AD-01
* **核心算法：行为指纹比对 (Behavioral Fingerprinting)**
* Agent 内部维护一套“健康交互指纹库”（如：标准的 Uniswap Swap 应该包含哪些 Event，涉及哪些槽位）。
* 当实时模拟的指纹偏离基准值超过 30% 时，LLM 必须介入进行深度推理（Deep Reasoning）。


* **Requirement ID:** FR-AD-02
* **动态策略生成 (Dynamic Policy Generation)**
* 当识别到疑似 0-day 行为时，Agent 不仅仅返回“危险”，还需要自主生成一份“风险证明文档”，解释为什么这个新奇的操作逻辑是不合理的，并将其作为 **Metadata** 返回给调用方。


---

## 5. 用户故事 (User Stories)

| 编号 | 角色 | 场景描述 | 智能体行为 |
| --- | --- | --- | --- |
| **US-01** | DeFi 交易者 | 用户准备在钓鱼网站签名 | Agent 自动介入，通过意图对比发现授权对象非官方合约，**主动阻断**并解释风险。 |
| **US-02** | 开发者 | 自动化 Agent 需要调用 SSSEA | 开发者通过标准 OpenAI SDK 调用 SSSEA，获得**带硬件签名**的执行报告，确保下游逻辑安全。 |
| **US-03** | 审计员 | 验证历史交易的安全性 | Agent 重构当时的区块环境，生成**可回溯**的模拟证明，展示漏洞触发点。 |

---

## 6. 非功能性需求与安全性 (NFRs)

* **零知识隐私：** 物理私钥解密过程仅限 TEE 内部，开发者及系统权限无法触达。
* **响应时延：** 完整的“感知-推理-模拟”链路需在 8 秒内完成，其中 TEE 启动不得超过 2 秒。
* **高可用性：** 模拟引擎需具备 RPC 自动故障转移（Failover）能力。

---

## 7. 路线图 (Roadmap)

* **M1 (Prototype):** 完成本地 Docker 化的 Anvil 模拟引擎及基础 OpenAI 接口。
* **M2 (Security Beta):** 集成 TEE 硬件环境，完成第一批 20 种 Web3 风险模式的 LLM 推理优化。
* **M3 (Sentient Spark):** 正式接入 Sentient GRID 网络，实现基于 OML 的自主收益结算。


### 📝 PRD 补充章节：智能体间协作协议 (Agent-to-Agent Protocol)

#### 1. 协作定位 (Cooperation Positioning)

SSSEA 不直接面对所有终端用户，而是作为 Sentient GRID 网络中的 **“安全审计背书节点”**。它通过标准的 OpenAI Function Calling 接口，为其他 **交易型智能体（Transaction Agents）** 提供异步或同步的审计服务。

#### 2. 交互逻辑流 (Interaction Logic Flow)

我们需要在 PRD 的 **“3. 功能需求”** 中增加以下子项：

* **FR-08 意图-数据对齐审计 (Intent-Data Alignment)：**
* Agent 必须支持同时接收 `User Intent` (自然语言) 和 `Proposed Transaction` (字节码)。
* LLM 必须执行推理：判断 `Transaction` 的执行后果是否在 `User Intent` 的语义范围内。


* **FR-09 递归证明回执 (OML Attestation Receipt)：**
* 响应必须包含符合 OML 1.0 标准的证明包，确保调用方（DeFi 助手）可以将此证明展示给终端用户。



#### 3. 接口规范更新 (API Schema Update)

我们需要定义一套专门用于 Agent 间“握手”的 API 结构。

**请求示例 (DeFi 助手 -> SSSEA):**

```json
{
  "agent_metadata": {
    "caller_id": "sentient-defi-assistant-001",
    "oml_loyalty_score": 95
  },
  "payload": {
    "intent": "在 Uniswap V3 上将 1 ETH 兑换为等值的 USDC，滑点容忍度 0.5%",
    "call_frame": {
      "to": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
      "data": "0x414bf389000000000000000000000000...", 
      "value": "1000000000000000000"
    }
  }
}

```

**响应示例 (SSSEA -> DeFi 助手):**

```json
{
  "audit_verdict": "PASS", 
  "confidence_score": 0.99,
  "analysis": "模拟显示该交易将获得 2500 USDC，符合当前市价及滑点设置。合约地址为 Uniswap V3 官方路由，无恶意代码逻辑。",
  "security_proof": {
    "tee_quote": "0xATT_QUOTE_DATA...",
    "verification_url": "https://verify.sentient.network/..."
  }
}

```

#### 4. 故障处理策略 (Error Handling)

在 Agent 协作中，PRD 必须定义“如果审计不通过”的逻辑：

* **拦截模式 (Intercept):** 若风险评级为 CRITICAL，SSSEA 必须返回明确的 `STOP` 指令。
* **降级建议 (Degrade):** 若风险源于滑点过高，SSSEA 必须返回 `ADVISE` 指令及推荐参数。