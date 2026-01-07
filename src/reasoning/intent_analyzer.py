"""
Intent Analyzer - 意图对齐审计核心

使用 LLM 对比用户意图与模拟执行结果，判断交易是否安全。
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field
from openai import AsyncOpenAI

from ..simulation.models import (
    SimulationRequest,
    SimulationResult,
    RiskLevel,
    AssetChange,
)
from .prompts import PromptTemplates, KnownRiskPatterns


logger = logging.getLogger(__name__)


def _max_risk(current: RiskLevel, new: RiskLevel) -> RiskLevel:
    """返回更高的风险等级"""
    risk_order = {RiskLevel.CRITICAL: 2, RiskLevel.WARNING: 1, RiskLevel.SAFE: 0}
    return max(current, new, key=lambda x: risk_order[x])


class IntentAnalysisResult(BaseModel):
    """意图分析结果"""
    risk_level: RiskLevel
    confidence: float  # 0.0 - 1.0
    summary: str
    analysis: str
    anomalies: List[str]
    recommendations: List[str]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # LLM 原始输出
    raw_response: Optional[str] = None

    # Token 使用统计
    prompt_tokens: int = 0
    completion_tokens: int = 0


class IntentAnalyzer:
    """
    意图分析器

    核心功能：
    1. 对比用户意图与模拟结果
    2. 检测风险模式
    3. 给出风险评级和建议
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
    ):
        """
        初始化意图分析器

        Args:
            api_key: OpenAI API Key
            base_url: API Base URL
            model: 使用的模型
        """
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model

    async def analyze(
        self,
        request: SimulationRequest,
        result: SimulationResult,
    ) -> IntentAnalysisResult:
        """
        执行意图对齐分析

        Args:
            request: 模拟请求（包含用户意图）
            result: 模拟执行结果

        Returns:
            IntentAnalysisResult: 分析结果
        """
        # 1. 首先进行基于规则的快速检查
        rule_based_result = self._rule_based_check(request, result)

        # 如果规则检查已经发现严重问题，直接返回
        if rule_based_result["risk_level"] == RiskLevel.CRITICAL:
            return IntentAnalysisResult(
                risk_level=RiskLevel.CRITICAL,
                confidence=1.0,
                summary=rule_based_result["summary"],
                analysis=rule_based_result["analysis"],
                anomalies=rule_based_result["anomalies"],
                recommendations=rule_based_result["recommendations"],
            )

        # 2. 构建 LLM Prompt
        prompt = PromptTemplates.build_intent_alignment_prompt(
            user_intent=request.user_intent,
            tx_from=request.tx_from,
            tx_to=request.tx_to,
            tx_value=request.tx_value,
            tx_data=request.tx_data,
            success=result.success,
            gas_used=result.gas_used,
            error_message=result.error_message or "",
            asset_changes=[
                {
                    "token_symbol": c.token_symbol,
                    "change_amount": c.change_amount,
                }
                for c in result.asset_changes
            ],
            call_trace_summary=self._summarize_call_traces(result.call_traces),
            detected_anomalies=result.anomalies,
        )

        # 3. 调用 LLM 进行深度分析
        llm_result = await self._call_llm(prompt)

        # 4. 合并规则和 LLM 的结果
        final_result = self._merge_results(rule_based_result, llm_result, result)

        return final_result

    def _rule_based_check(
        self,
        request: SimulationRequest,
        result: SimulationResult,
    ) -> Dict[str, Any]:
        """
        基于规则的快速检查

        检查项：
        1. 交易是否失败
        2. 是否有异常的 ETH 转出
        3. 调用深度是否过深（重入风险）
        4. 是否有危险的函数调用
        """
        risk_level = RiskLevel.SAFE
        anomalies = []
        recommendations = []
        summary = "基于规则的初步检查通过"
        analysis = ""

        # 检查 1: 交易失败
        if not result.success:
            risk_level = RiskLevel.WARNING
            summary = "交易执行失败"
            analysis = f"交易在模拟中失败，可能原因：{result.error_message or '未知错误'}"
            anomalies.append(f"交易执行失败: {result.error_message}")
            recommendations.append("检查交易参数和合约状态")

        # 检查 2: 异常的 ETH 转出
        tx_value_int = int(request.tx_value) if not request.tx_value.startswith("0x") else int(request.tx_value, 16)
        for change in result.asset_changes:
            if change.token_symbol == "ETH":
                change_int = int(change.change_amount)
                # 如果转出的 ETH 超过 tx_value，说明有额外的转出
                if change_int < -tx_value_int:
                    risk_level = RiskLevel.CRITICAL
                    summary = "检测到异常的 ETH 转出"
                    extra_out = abs(change_int) - tx_value_int
                    anomalies.append(f"异常 ETH 转出: 额外转出 {extra_out / 1e18:.4f} ETH")
                    recommendations.append("立即停止交易，这可能是钓鱼攻击")

        # 检查 3: 调用深度（重入风险）
        if result.call_traces:
            max_depth = max(t.depth for t in result.call_traces)
            if max_depth > 20:
                risk_level = _max_risk(risk_level, RiskLevel.WARNING)
                anomalies.append(f"调用深度过深 ({max_depth})，可能存在重入风险")
                recommendations.append("检查合约是否存在重入漏洞")

        # 检查 4: 危险的函数选择器
        selector = KnownRiskPatterns.extract_function_selector(request.tx_data)
        func_name = KnownRiskPatterns.get_function_name(selector)
        if func_name != "unknown":
            # 检查是否为官方合约
            is_official = KnownRiskPatterns.is_official_contract(
                "ethereum", request.tx_to
            )
            if not is_official:
                risk_level = _max_risk(risk_level, RiskLevel.WARNING)
                anomalies.append(f"检测到敏感函数调用: {func_name}")
                recommendations.append(f"确认 {request.tx_to} 是可信的官方合约")

        # 检查 5: 资产变动是否与意图一致
        if "swap" in request.user_intent.lower() and result.asset_changes:
            # 用户想 swap，应该有资产减少和增加
            has_decrease = any(int(c.change_amount) < 0 for c in result.asset_changes)
            has_increase = any(int(c.change_amount) > 0 for c in result.asset_changes)
            if not (has_decrease and has_increase) and result.success:
                risk_level = _max_risk(risk_level, RiskLevel.WARNING)
                anomalies.append("Swap 交易后资产变动异常")
                recommendations.append("验证交易是否真的执行了兑换")

        return {
            "risk_level": risk_level,
            "confidence": 0.8,
            "summary": summary,
            "analysis": analysis,
            "anomalies": anomalies,
            "recommendations": recommendations,
        }

    def _summarize_call_traces(self, traces: List) -> str:
        """总结调用栈"""
        if not traces:
            return "无调用数据"

        summary = []
        for trace in traces[:5]:  # 只显示前 5 个
            summary.append(
                f"[深度{trace.depth}] {trace.from_address} -> {trace.to_address}"
                + (f" (${int(trace.value) / 1e18:.4f} ETH)" if int(trace.value) > 0 else "")
            )

        if len(traces) > 5:
            summary.append(f"... 还有 {len(traces) - 5} 个调用")

        return "\n".join(summary)

    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """
        调用 LLM 进行深度分析

        Args:
            prompt: 完整的 prompt

        Returns:
            LLM 分析结果
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": PromptTemplates.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # 低温度以获得一致的结果
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            return {
                "risk_level": RiskLevel(result.get("risk_level", "SAFE")),
                "confidence": result.get("confidence", 0.5),
                "summary": result.get("summary", ""),
                "analysis": result.get("analysis", ""),
                "anomalies": result.get("anomalies", []),
                "recommendations": result.get("recommendations", []),
                "raw_response": content,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            }

        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            # 返回保守的默认结果
            return {
                "risk_level": RiskLevel.WARNING,
                "confidence": 0.5,
                "summary": "LLM 分析失败，请人工审核",
                "analysis": f"分析服务暂时不可用: {str(e)}",
                "anomalies": [],
                "recommendations": ["建议人工审核此交易"],
                "raw_response": None,
                "prompt_tokens": 0,
                "completion_tokens": 0,
            }

    def _merge_results(
        self,
        rule_based: Dict[str, Any],
        llm_based: Dict[str, Any],
        result: SimulationResult,
    ) -> IntentAnalysisResult:
        """
        合并规则检查和 LLM 分析的结果

        策略：
        1. 风险等级取两者中较高的
        2. 合并异常列表
        3. 优先使用 LLM 的分析文本
        """
        # 风险等级取较高者（CRITICAL > WARNING > SAFE）
        risk_order = {RiskLevel.CRITICAL: 2, RiskLevel.WARNING: 1, RiskLevel.SAFE: 0}
        final_risk = max(
            rule_based["risk_level"],
            llm_based["risk_level"],
            key=lambda x: risk_order[x],
        )

        # 合并异常（去重）
        all_anomalies = list(set(
            rule_based["anomalies"] + llm_based["anomalies"] + result.anomalies
        ))

        # 合并建议
        all_recommendations = list(set(
            rule_based["recommendations"] + llm_based["recommendations"]
        ))

        # 如果是 CRITICAL，更新 result
        result.risk_level = final_risk
        result.anomalies = all_anomalies
        result.intent_analysis = llm_based.get("analysis", rule_based["analysis"])

        return IntentAnalysisResult(
            risk_level=final_risk,
            confidence=max(rule_based["confidence"], llm_based["confidence"]),
            summary=llm_based.get("summary", rule_based["summary"]),
            analysis=llm_based.get("analysis", rule_based["analysis"]),
            anomalies=all_anomalies,
            recommendations=all_recommendations,
            raw_response=llm_based.get("raw_response"),
            prompt_tokens=llm_based.get("prompt_tokens", 0),
            completion_tokens=llm_based.get("completion_tokens", 0),
        )


class MockIntentAnalyzer(IntentAnalyzer):
    """
    Mock 意图分析器

    用于测试和 MVP 阶段，不调用真实的 LLM。
    """

    def __init__(self):
        """不需要 API Key"""
        pass

    async def analyze(
        self,
        request: SimulationRequest,
        result: SimulationResult,
    ) -> IntentAnalysisResult:
        """
        Mock 分析逻辑

        简单规则：
        1. 如果交易失败 -> WARNING
        2. 如果有异常转出 -> CRITICAL
        3. 否则 -> SAFE
        """
        rule_based = self._rule_based_check(request, result)

        return IntentAnalysisResult(
            risk_level=rule_based["risk_level"],
            confidence=rule_based["confidence"],
            summary=rule_based["summary"],
            analysis=rule_based["analysis"] or "Mock 分析：基于规则的快速检查",
            anomalies=rule_based["anomalies"],
            recommendations=rule_based["recommendations"],
            raw_response="mock_response",
        )
