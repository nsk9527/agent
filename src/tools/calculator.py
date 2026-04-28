import ast
import operator


class CalculatorTool:
    name = "calculator"
    desc = "一个安全的计算器工具，接受字符串形式的数学公式（如 '1 + 2 * 3'），返回计算结果。支持 +、-、*、/、//、%、** 运算以及括号。"
    description = desc

    # 允许的安全运算符映射
    _OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def __call__(self, expression: str) -> str:
        return self.run(expression)

    def run(self, expression: str) -> str:
        print(f"🧮 正在执行计算: {expression}")
        try:
            result = self._evaluate(expression)
            return str(result)
        except ZeroDivisionError:
            return "[ERROR:INVALID_EXPRESSION] 错误: 除数不能为零。"
        except (ValueError, TypeError, SyntaxError) as e:
            return f"[ERROR:INVALID_EXPRESSION] 错误: 表达式无效或包含不允许的运算。详细信息: {e}"
        except Exception as e:
            return f"[ERROR:EXECUTION] 计算时发生错误: {e}"

    def _evaluate(self, expression: str):
        """安全地解析并计算数学表达式。"""
        node = ast.parse(expression.strip(), mode="eval")
        return self._eval_node(node.body)

    def _eval_node(self, node):
        if isinstance(node, ast.Expression):
            return self._eval_node(node.body)

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"不允许的字面量类型: {type(node.value).__name__}")

        if isinstance(node, ast.Num):  # Python < 3.8 兼容
            return node.n

        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self._OPERATORS:
                raise ValueError(f"不允许的二元运算符: {op_type.__name__}")
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return self._OPERATORS[op_type](left, right)

        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self._OPERATORS:
                raise ValueError(f"不允许的一元运算符: {op_type.__name__}")
            operand = self._eval_node(node.operand)
            return self._OPERATORS[op_type](operand)

        if isinstance(node, ast.Call):
            raise ValueError("不允许函数调用")

        if isinstance(node, ast.Name):
            raise ValueError("不允许变量引用")

        if isinstance(node, ast.Subscript):
            raise ValueError("不允许下标操作")

        raise ValueError(f"不支持的表达式节点: {type(node).__name__}")
