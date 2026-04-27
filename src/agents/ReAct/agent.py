import re
import json

from ...tools.ToolExecutor import ToolExecutor
from .prompt import REACT_PROMPT_TEMPLATE
from ..baseAgent import BaseAgent


class ReActAgent:
    def __init__(self, llm_client: BaseAgent, tool_executor: ToolExecutor, max_steps: int = 5):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history = []

    def run(self, question: str):
        """
        运行ReAct智能体来回答一个问题。
        """
        self.history = []  # 每次运行时重置历史记录
        current_step = 0

        while current_step < self.max_steps:
            current_step += 1
            print(f"--- 第 {current_step} 步 ---")

            # 1. 格式化提示词
            tools_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history)
            prompt = REACT_PROMPT_TEMPLATE.format(
                tools=tools_desc,
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
                observation = f"错误:未找到名为 '{tool_name}' 的工具。"
            else:
                observation = tool_function(tool_input)  # 调用真实工具

            # (这段逻辑紧随工具调用之后，在 while 循环的末尾)
            print(f"👀 观察: {observation}")

            # 将本轮的Action和Observation添加到历史记录中
            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")

            # 循环结束
        print("已达到最大步数，流程终止。")
        return None

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
