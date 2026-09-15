import ast
import operator


def calculator(expression: str):
    print("TOOL CALL ☎️ calculator", "arg:", expression)

    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def evaluate(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value

        if isinstance(node, ast.BinOp) and type(node.op) in operators:
            left = evaluate(node.left)
            right = evaluate(node.right)
            return operators[type(node.op)](left, right)

        if isinstance(node, ast.UnaryOp) and type(node.op) in operators:
            return operators[type(node.op)](evaluate(node.operand))

        raise ValueError("Unsupported expression")

    try:
        tree = ast.parse(expression, mode="eval")
        result = evaluate(tree.body)

        return {
            "expression": expression,
            "result": result
        }

    except Exception as e:
        return {
            "expression": expression,
            "error": str(e)
        }

