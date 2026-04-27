from .tools.search import SearchTool
from .tools.calculator import CalculatorTool
from .tools.ToolExecutor import ToolExecutor
from .agents.ReAct.agent import ReActAgent
from .agents.PlanAndSolve.agent import PlanAndSolveAgent
from .agents.Reflection.agent import ReflectionAgent
from .agents.baseAgent import BaseAgent


def reActAgent():
    try:
        llm_client = BaseAgent()
        tool_executor = ToolExecutor()
        search_tool = SearchTool()
        calculator_tool = CalculatorTool()
        tool_executor.registerTool(search_tool)
        tool_executor.registerTool(calculator_tool)
        agent = ReActAgent(llm_client, tool_executor)
        agent.run("40个梨分给3个班，分给一班20个，其余平均分给二班和三班，二班分到几个")
    except ValueError as e:
        print(e)


def planAndSolveAgent():
    try:
        llm_client = BaseAgent()
        agent = PlanAndSolveAgent(llm_client)
        agent.run("一个水果店周一卖出了15个苹果。周二卖出的苹果数量是周一的两倍。周三卖出的数量比周二少了5个。请问这三天总共卖出了多少个苹果？")
    except ValueError as e:
        print(e)

def reflectionAgent():
    try:
        llm_client = BaseAgent()
        agent = ReflectionAgent(llm_client)
        agent.run("编写一个Python函数，找出1到n之间所有的素数")
    except ValueError as e:
        print(e)

def main():
    try:
        reActAgent()
    except ValueError as e:
        print(e)
