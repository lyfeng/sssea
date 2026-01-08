"""
Base Agent Interface for ROMA

定义ROMA Agent的基础接口，确保所有Agent类遵循统一规范。
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class AgentContext(BaseModel):
    """Agent执行上下文"""
    # 输入数据
    user_intent: str = Field(..., description="用户意图")
    tx_data: Dict[str, Any] = Field(default_factory=dict, description="交易数据")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    # 执行状态
    current_step: str = "perception"
    step_history: List[str] = Field(default_factory=list, description="执行历史")

    # 中间结果
    simulation_result: Optional[Dict[str, Any]] = None
    analysis_result: Optional[Dict[str, Any]] = None

    # 配置
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent配置")

    def add_history(self, step: str) -> None:
        """添加执行历史"""
        self.step_history.append(step)
        self.current_step = step


class AgentResult(BaseModel):
    """Agent执行结果"""
    agent_name: str = Field(..., description="Agent名称")
    success: bool = Field(..., description="执行是否成功")
    execution_time: float = Field(..., description="执行时间（秒）")
    data: Dict[str, Any] = Field(default_factory=dict, description="返回数据")
    error: Optional[str] = Field(None, description="错误信息")
    next_step: Optional[str] = Field(None, description="下一步建议")
    confidence: float = Field(1.0, description="结果置信度")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="执行时间戳")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return self.model_dump()


class BaseAgent(ABC):
    """
    ROMA Agent基础类

    所有SSSEA的Agent都应该继承这个类，实现ROMA标准接口。
    """

    agent_name: str = "base_agent"
    description: str = "Base agent for ROMA"

    def __init__(self, config: Optional[Dict[str, Any]] = None, toolkits: Optional[Dict[str, Any]] = None):
        """
        初始化Agent

        Args:
            config: Agent配置
            toolkits: 可用的工具集
        """
        self.config = config or {}
        self.toolkits = toolkits or {}
        self._initialize()

    def _initialize(self) -> None:
        """子类可重写此方法进行自定义初始化"""
        pass

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        执行Agent的主要逻辑

        Args:
            context: Agent执行上下文

        Returns:
            AgentResult: 执行结果
        """
        raise NotImplementedError

    async def pre_process(self, context: AgentContext) -> AgentContext:
        """
        执行前处理

        Args:
            context: Agent上下文

        Returns:
            AgentContext: 处理后的上下文
        """
        return context

    async def post_process(
        self,
        context: AgentContext,
        result: AgentResult
    ) -> AgentResult:
        """
        执行后处理

        Args:
            context: Agent上下文
            result: 执行结果

        Returns:
            AgentResult: 处理后的结果
        """
        return result

    async def __call__(self, context: AgentContext) -> AgentResult:
        """使Agent可被直接调用"""
        start = time.time()

        # 执行前处理
        context = await self.pre_process(context)

        # 执行主要逻辑
        result = await self.execute(context)

        # 执行后处理
        result = await self.post_process(context, result)

        # 设置执行时间
        result.execution_time = time.time() - start
        result.agent_name = self.agent_name

        # 更新上下文
        context.add_history(self.agent_name)

        return result

    def get_toolkit(self, name: str) -> Optional[Any]:
        """获取指定的工具"""
        return self.toolkits.get(name)

    def has_toolkit(self, name: str) -> bool:
        """检查工具是否可用"""
        return name in self.toolkits
