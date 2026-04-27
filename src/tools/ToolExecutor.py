from typing import Dict, Any

class ToolExecutor:
    """
    一个工具执行器，负责管理和执行工具。
    """
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}

    def registerTool(self, tool: Any):
        """
        向工具箱中注册一个新工具。
        """
        name = getattr(tool, "name", None)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("工具注册失败: tool.name 必须是非空字符串。")

        description = getattr(tool, "description", None)
        if description is None:
            description = getattr(tool, "desc", "")
        if description is None:
            description = ""
        if not isinstance(description, str):
            raise ValueError("工具注册失败: tool.description/tool.desc 必须是字符串。")

        func = getattr(tool, "run", None)
        if not callable(func):
            raise ValueError("工具注册失败: tool.run 必须是可调用的函数。")

        if name in self.tools:
            print(f"警告:工具 '{name}' 已存在，将被覆盖。")
        self.tools[name] = {"description": description, "func": func, "tool": tool}
        print(f"工具 '{name}' 已注册。")

    def getTool(self, name: str) -> callable:
        """
        根据名称获取一个工具的执行函数。
        """
        return self.tools.get(name, {}).get("func")

    def getAvailableTools(self) -> str:
        """
        获取所有可用工具的格式化描述字符串。
        """
        return "\n".join([
            f"- {name}: {info['description']}"
            for name, info in self.tools.items()
        ])
