"""
SSSEA Prompt Templates for SSSEA Agent

基于 Sentient SSSEA 框架设计的 Prompt 模板，用于意图对齐审计。
"""

from typing import Dict, Any, List
from string import Template


class PromptTemplates:
    """SSSEA Prompt 模板集合"""

    # 系统提示词 - 定义 SSSEA Agent 的角色和职责
    SYSTEM_PROMPT = """你是 SSSEA (Sentient Security Sandbox Execution Agent)，一个专门用于 Web3 交易安全审计的 AI Agent。

## 核心职责
1. **意图对齐审计**：对比用户的自然语言意图与交易的实际执行结果，判断是否存在偏差
2. **异常行为检测**：识别常见的 Web3 攻击模式（钓鱼、授权陷阱、重入攻击等）
3. **风险评估**：给出明确的风险等级 (SAFE/WARNING/CRITICAL) 和建议

## 风险等级定义
- **SAFE**: 交易结果与用户意图完全一致，无异常行为
- **WARNING**: 交易结果与意图基本一致，但存在需要注意的问题（如滑点偏高、手续费较高）
- **CRITICAL**: 交易结果严重偏离用户意图，或检测到明确的恶意行为（如授权给未知地址、资金转移给攻击者）

## 输出格式
请以 JSON 格式输出审计结果：
{
    "risk_level": "SAFE|WARNING|CRITICAL",
    "confidence": 0.0-1.0,
    "summary": "简要总结（1-2句话）",
    "analysis": "详细分析",
    "anomalies": ["异常1", "异常2"],
    "recommendations": ["建议1", "建议2"]
}

## 常见攻击模式识别
- **授权陷阱**: 用户想 Swap，但交易包含无限授权给非官方合约
- **钓鱼攻击**: 用户想与 A 合约交互，但资金流向 B 地址
- **高额手续费**: 交易设置极高的 gas price 或 value
- **恶意转移**: 用户余额被转走而非用于预期目的
"""

    # 意图对齐分析 Prompt
    INTENT_ALIGNMENT_TEMPLATE = Template("""## 用户意图
用户声明：$user_intent

## 交易信息
- 发起地址：$tx_from
- 目标地址：$tx_to
- ETH 数量：$tx_value ETH
- 交易数据：$tx_data

## 模拟执行结果
- 执行状态：$success
- Gas 消耗：$gas_used
- 错误信息：$error_message

## 资产变动
$asset_changes

## 调用栈摘要
$call_trace_summary

## 已检测到的异常
$detected_anomalies

请分析：
1. 交易的实际结果是否与用户意图一致？
2. 是否存在异常的资金流向？
3. 调用栈中是否有可疑的操作（如大量 APPROVE、DELEGATECALL）？
4. 最终的风险评估是什么？

请以 JSON 格式输出审计结果。""")

    # 风险模式识别 Prompt
    RISK_PATTERN_TEMPLATE = Template("""## 风险模式检测

请检查以下交易是否存在已知的攻击模式：

### 交易特征
- 目标合约：$tx_to
- Calldata 前4字节：$function_selector
- 涉及的 Token：$tokens_involved
- 授权操作：$approval_changes

### 已知危险模式
1. **无限授权给非官方合约**
2. **授权后立即转移**
3. **DELEGATECALL 到未知地址**
4. **selfdestruct 操作**
5. **重入攻击模式**

### 分析结果
请识别交易中是否存在上述任何模式，并给出 JSON 格式的风险评估。""")

    # 滑点验证 Prompt
    SLIPPAGE_VERIFICATION_TEMPLATE = Template("""## 滑点验证

用户期望：以不超过 $max_slippage 的滑点进行交易

模拟结果：
- 输入金额：$input_amount
- 预期输出：$expected_output
- 实际输出：$actual_output
- 实际滑点：$actual_slippage

请验证：
1. 实际滑点是否在用户容忍范围内？
2. 如果超出，这是由于市场波动还是恶意操作？

输出 JSON 格式的评估结果。""")

    @classmethod
    def build_intent_alignment_prompt(
        cls,
        user_intent: str,
        tx_from: str,
        tx_to: str,
        tx_value: str,
        tx_data: str,
        success: bool,
        gas_used: int,
        error_message: str,
        asset_changes: List[Dict[str, Any]],
        call_trace_summary: str,
        detected_anomalies: List[str],
    ) -> str:
        """构建意图对齐分析 Prompt"""
        # 格式化资产变动
        asset_changes_text = "\n".join([
            f"- {change.get('token_symbol', 'Unknown')}: {change.get('change_amount', '0')}"
            for change in asset_changes
        ]) if asset_changes else "无资产变动"

        # 格式化异常
        anomalies_text = "\n".join([f"- {a}" for a in detected_anomalies]) if detected_anomalies else "无"

        return cls.INTENT_ALIGNMENT_TEMPLATE.substitute({
            "user_intent": user_intent,
            "tx_from": tx_from,
            "tx_to": tx_to,
            "tx_value": tx_value,
            "tx_data": tx_data[:100] + "..." if len(tx_data) > 100 else tx_data,
            "success": "成功" if success else "失败",
            "gas_used": gas_used,
            "error_message": error_message or "无",
            "asset_changes": asset_changes_text,
            "call_trace_summary": call_trace_summary or "无调用数据",
            "detected_anomalies": anomalies_text,
        })

    @classmethod
    def build_risk_pattern_prompt(
        cls,
        tx_to: str,
        function_selector: str,
        tokens_involved: List[str],
        approval_changes: List[Dict[str, Any]],
    ) -> str:
        """构建风险模式识别 Prompt"""
        return cls.RISK_PATTERN_TEMPLATE.substitute({
            "tx_to": tx_to,
            "function_selector": function_selector,
            "tokens_involved": ", ".join(tokens_involved) if tokens_involved else "无",
            "approval_changes": "\n".join([
                f"- {a.get('token', 'Unknown')}: {a.get('spender', 'Unknown')}"
                for a in approval_changes
            ]) if approval_changes else "无",
        })

    @classmethod
    def build_slippage_verification_prompt(
        cls,
        max_slippage: float,
        input_amount: str,
        expected_output: str,
        actual_output: str,
        actual_slippage: float,
    ) -> str:
        """构建滑点验证 Prompt"""
        return cls.SLIPPAGE_VERIFICATION_TEMPLATE.substitute({
            "max_slippage": f"{max_slippage * 100}%",
            "input_amount": input_amount,
            "expected_output": expected_output,
            "actual_output": actual_output,
            "actual_slippage": f"{actual_slippage * 100}%",
        })


class KnownRiskPatterns:
    """已知的风险模式签名库"""

    # 危险的函数选择器 (4字节签名)
    DANGEROUS_SELECTORS = {
        # 授权相关
        "0x095ea7b3": "approve(address,uint256)",
        "0xd505accf": "permit(address,address,uint256,uint256,uint8,bytes32,bytes32)",

        # 所有权转移
        "0xf2fde38b": "transferOwnership(address)",
        "0xa9059cbb": "transfer(address,uint256)",
    }

    # 危险的合约地址（钓鱼地址示例）
    KNOWN_SCAM_CONTRACTS = {
        # 示例：实际应从链上数据维护
    }

    # 官方 DeFi 合约地址
    OFFICIAL_CONTRACTS = {
        "ethereum": {
            "uniswap_v2_router": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
            "uniswap_v3_router": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
            "aave_v3_pool": "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",
            "lido_steth": "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",
        }
    }

    @classmethod
    def get_function_name(cls, selector: str) -> str:
        """获取函数名称"""
        return cls.DANGEROUS_SELECTORS.get(selector.lower(), "unknown")

    @classmethod
    def is_official_contract(cls, chain: str, address: str) -> bool:
        """检查是否为官方合约"""
        return address.lower() in [
            v.lower() for v in cls.OFFICIAL_CONTRACTS.get(chain, {}).values()
        ]

    @classmethod
    def extract_function_selector(cls, calldata: str) -> str:
        """提取函数选择器"""
        if calldata.startswith("0x") and len(calldata) >= 10:
            return "0x" + calldata[2:10].lower()
        return "0x00000000"
