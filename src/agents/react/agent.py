import re
import json

from ...tools.tool_executor import ToolExecutor
from .prompt import REACT_PROMPT_TEMPLATE
from ..base_agent import BaseAgent


class ReActAgent:
    def __init__(self, llm_client: BaseAgent, tool_executor: ToolExecutor, max_steps: int = 5):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history = []
        self.tool_failures = {}  # {tool_name: {"count": int, "last_error": str}}
        self.max_failures = 3

    def run(self, question: str):
        """
        运行ReAct智能体来回答一个问题。
        """
        self.history = []  # 每次运行时重置历史记录
        self.tool_failures = {}  # 每次对话重置失败记录
        current_step = 0

        while current_step < self.max_steps:
            current_step += 1
            print(f"--- 第 {current_step} 步 ---")

            # 1. 格式化提示词
            tools_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history)
            hints = self._build_hints()
            prompt = REACT_PROMPT_TEMPLATE.format(
                tools=tools_desc,
                hints=hints,
                question=question,
                history=history_str
            )

            # 2. 调用LLM进行思考
            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages)

            if not response_text:
                print("错误:LLM未能返回有效响应。")
                break

            # 3. 解析LLM的输出
            thought, action = self._parse_output(response_text)

            if thought:
                print(f"思考: {thought}")

            if not action:
                print("警告:未能解析出有效的Action，流程终止。")
                break

            # 4. 执行Action
            if action.startswith("Finish"):
                # 如果是Finish指令，提取最终答案并结束
                final_answer = self._parse_finish(action)
                if final_answer is None:
                    print("错误:Finish[...] 格式解析失败，流程终止。")
                    break
                print(f"🎉 最终答案: {final_answer}")
                return final_answer

            tool_name, tool_input = self._parse_action(action)
            if not tool_name or not tool_input:
                # ... 处理无效Action格式 ...
                continue

            print(f"🎬 行动: {tool_name}[{tool_input}]")

            tool_function = self.tool_executor.getTool(tool_name)
            if not tool_function:
                observation = f"[ERROR:NOT_FOUND] 错误:未找到名为 '{tool_name}' 的工具。"
            else:
                try:
                    observation = tool_function(tool_input)  # 调用真实工具
                except Exception as e:
                    observation = f"[ERROR:EXECUTION] 错误:工具执行异常: {e}"

            # 失败跟踪与提示注入
            error_type = self._classify_error(observation)
            if error_type:
                fail_record = self.tool_failures.setdefault(
                    tool_name, {"count": 0, "last_error": error_type}
                )
                fail_record["count"] += 1
                fail_record["last_error"] = error_type
            else:
                # 成功则清除该工具的失败记录
                self.tool_failures.pop(tool_name, None)

            # (这段逻辑紧随工具调用之后，在 while 循环的末尾)
            print(f"👀 观察: {observation}")

            # 将本轮的Action和Observation添加到历史记录中
            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")

            # 循环结束
        print("已达到最大步数，流程终止。")
        return None

    def _classify_error(self, observation: str) -> str | None:
        """从 observation 中解析错误类型。返回 None 表示未检测到错误。"""
        match = re.match(r"\[ERROR:([A-Z_]+)\]", observation)
        if match:
            return match.group(1)
        # 兼容旧格式的错误字符串
        if "错误" in observation:
            return "UNKNOWN"
        return None

    def _build_hints(self) -> str:
        """根据工具失败记录生成提示字符串。"""
        if not self.tool_failures:
            return ""

        hints = []
        for tool_name, record in self.tool_failures.items():
            if record["count"] >= self.max_failures:
                hint = self._generate_hint(tool_name, record)
                hints.append(hint)

        if not hints:
            return ""

        return "\n【系统提示】\n" + "\n".join(hints) + "\n"

    def _generate_hint(self, tool_name: str, record: dict) -> str:
        """根据错误类型生成针对性的恢复提示。"""
        error_type = record["last_error"]
        count = record["count"]

        if error_type in ("INVALID_ARGUMENT", "INVALID_EXPRESSION"):
            return (
                f"- 工具 '{tool_name}' 已连续失败 {count} 次（参数错误）。"
                f"请仔细检查输入格式是否正确，或尝试换用其他工具。"
            )
        elif error_type in ("NETWORK", "TIMEOUT", "EXECUTION"):
            return (
                f"- 工具 '{tool_name}' 已连续失败 {count} 次（服务异常）。"
                f"该工具当前可能不可用，建议换用其他工具或直接给出已知信息。"
            )
        elif error_type == "EMPTY_RESULT":
            return (
                f"- 工具 '{tool_name}' 已连续失败 {count} 次（无结果）。"
                f"请尝试更换关键词或调整查询策略。"
            )
        elif error_type == "NOT_FOUND":
            return (
                f"- 工具 '{tool_name}' 不存在，请只使用可用工具列表中的工具。"
            )
        else:
            return (
                f"- 工具 '{tool_name}' 已连续失败 {count} 次。"
                f"请尝试调整参数或换用其他工具。"
            )

    def _parse_output(self, text: str):
        # 1) 优先解析 "Thought: ...\nAction: ..." 这种纯文本格式
        if "Thought:" in text and "Action:" in text:
            thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
            action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
            thought = thought_match.group(1).strip() if thought_match else ""
            action = action_match.group(1).strip() if action_match else ""
            return thought, action

        # 2) 再尝试解析 JSON 格式（纯 JSON / 代码块 / 前后带多余文本）
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r"\s*```$", "", cleaned)

            start = cleaned.find("{")
            if start == -1:
                print("错误:LLM输出不包含可解析的 Thought/Action，解析失败。")
                return None, None

            try:
                decoder = json.JSONDecoder()
                data, _end = decoder.raw_decode(cleaned[start:])
            except json.JSONDecodeError as e:
                print(f"错误:LLM输出JSON解析失败: {e}")
                return None, None

        thought = str(data.get("Thought", "")).strip()
        action = str(data.get("Action", "")).strip()
        return thought, action

    def _parse_action(self, action_text: str):
        """解析Action字符串，提取工具名称和输入。
        """
        match = re.match(r"(\w+)\[(.*)\]", action_text, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return None, None

    def _parse_finish(self, action_text: str):
        """解析 Finish[...] 动作，支持多行最终答案。"""
        action_text = action_text.strip()
        if not action_text.startswith("Finish[") or not action_text.endswith("]"):
            return None
        return action_text[len("Finish["):-1]
