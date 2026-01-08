"""
Base Toolkit Interface for ROMA

定义ROMA Toolkit的基础接口，确保所有工具类遵循统一规范。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ToolkitResult(BaseModel):
    """Toolkit执行结果的标准格式"""
    success: bool = Field(..., description="执行是否成功")
    tool_name: str = Field(..., description="工具名称")
    execution_time: float = Field(..., description="执行时间（秒）")
    data: Dict[str, Any] = Field(default_factory=dict, description="返回数据")
    error: Optional[str] = Field(None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="执行时间戳")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于ROMA Executor处理"""
        return self.model_dump()


class BaseToolkit(ABC):
    """
    ROMA Toolkit基础类

    所有SSSEA的Toolkit都应该继承这个类，实现ROMA标准接口。
    """

    tool_name: str = "base_toolkit"
    description: str = "Base toolkit for ROMA"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Toolkit

        Args:
            config: 工具配置字典
        """
        self.config = config or {}
        self._initialize()

    def _initialize(self) -> None:
        """子类可重写此方法进行自定义初始化"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolkitResult:
        """
        执行工具的主要逻辑

        Args:
            **kwargs: 工具执行参数

        Returns:
            ToolkitResult: 标准化的执行结果
        """
        raise NotImplementedError

    async def validate_input(self, **kwargs) -> tuple[bool, Optional[str]]:
        """
        验证输入参数

        Args:
            **kwargs: 输入参数

        Returns:
            (is_valid, error_message): 验证结果和错误信息
        """
        return True, None

    def get_schema(self) -> Dict[str, Any]:
        """
        获取工具的参数schema

        Returns:
            JSON Schema格式的参数定义
        """
        return {
            "name": self.tool_name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
            },
        }

    async def __call__(self, **kwargs) -> ToolkitResult:
        """使Toolkit可被直接调用"""
        import time
        start = time.time()

        # 验证输入
        is_valid, error = await self.validate_input(**kwargs)
        if not is_valid:
            return ToolkitResult(
                success=False,
                tool_name=self.tool_name,
                execution_time=time.time() - start,
                error=f"输入验证失败: {error}",
            )

        # 执行工具逻辑
        try:
            result = await self.execute(**kwargs)
            result.execution_time = time.time() - start
            return result
        except Exception as e:
            return ToolkitResult(
                success=False,
                tool_name=self.tool_name,
                execution_time=time.time() - start,
                error=str(e),
            )


class ToolkitRegistry:
    """
    Toolkit注册表

    管理所有可用的Toolkit，供ROMA Executor调用。
    """

    def __init__(self):
        self._tools: Dict[str, BaseToolkit] = {}

    def register(self, tool: BaseToolkit) -> None:
        """注册一个Toolkit"""
        self._tools[tool.tool_name] = tool

    def get(self, name: str) -> Optional[BaseToolkit]:
        """获取指定名称的Toolkit"""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """列出所有已注册的Toolkit名称"""
        return list(self._tools.keys())

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """获取所有Toolkit的Schema"""
        return [tool.get_schema() for tool in self._tools.values()]

    async def execute(self, tool_name: str, **kwargs) -> ToolkitResult:
        """
        执行指定的Toolkit

        Args:
            tool_name: 工具名称
            **kwargs: 执行参数

        Returns:
            ToolkitResult: 执行结果
        """
        tool = self.get(tool_name)
        if tool is None:
            return ToolkitResult(
                success=False,
                tool_name=tool_name,
                execution_time=0.0,
                error=f"工具 '{tool_name}' 未找到",
            )
        return await tool(**kwargs)
