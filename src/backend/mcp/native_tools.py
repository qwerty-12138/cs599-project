"""Native (built-in) tools that don't require MCP"""
import datetime
import logging

logger = logging.getLogger(__name__)

# Built-in tool definitions
NATIVE_TOOLS = [
    {
        "name": "calculate",
        "description": "执行数学计算。传入数学表达式如 '2 + 2'、'sqrt(16)'、'3 * 7' 等，返回计算结果。",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "要计算的数学表达式"
                }
            },
            "required": ["expression"]
        }
    },
    {
        "name": "get_current_time",
        "description": "获取当前日期和时间。可选的 timezone 参数指定时区（如 'Asia/Shanghai'、'UTC'），默认返回北京时间。",
        "input_schema": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "时区标识符，如 Asia/Shanghai、UTC、America/New_York"
                }
            }
        }
    },
]


class NativeToolRegistry:
    """Registry for executing native tools."""

    def __init__(self):
        self._tools = {}
        for t in NATIVE_TOOLS:
            self._tools[t["name"]] = t

    def get_tool_definitions(self) -> list[dict]:
        """Return tool definitions in OpenAI function-calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                }
            }
            for t in NATIVE_TOOLS
        ]

    async def execute(self, tool_name: str, args: dict) -> str:
        """Execute a native tool and return the result string."""
        if tool_name == "calculate":
            return self._calculate(args.get("expression", ""))
        elif tool_name == "get_current_time":
            return self._get_time(args.get("timezone", "Asia/Shanghai"))
        else:
            raise ValueError(f"Unknown native tool: {tool_name}")

    def _calculate(self, expression: str) -> str:
        try:
            # Safe eval using only math operations
            import math
            allowed_names = {
                k: v for k, v in math.__dict__.items()
                if not k.startswith("__")
            }
            allowed_names.update({"abs": abs, "round": round, "max": max, "min": min, "sum": sum})
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return str(result)
        except Exception as e:
            return f"计算错误: {e}"

    def _get_time(self, timezone: str = "Asia/Shanghai") -> str:
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo(timezone)
            now = datetime.datetime.now(tz)
            return now.strftime("%Y-%m-%d %H:%M:%S %Z")
        except Exception:
            now = datetime.datetime.now()
            return now.strftime("%Y-%m-%d %H:%M:%S UTC+8 (默认)")


native_tool_registry = NativeToolRegistry()
