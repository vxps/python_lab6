from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import ast
import operator

app = FastAPI(title="Калькулятор с поддержкой сложных выражений")

class SafeEval:
    _operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
    }

    @classmethod
    def _eval_node(cls, node):
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.BinOp):
            left = cls._eval_node(node.left)
            right = cls._eval_node(node.right)
            op = cls._operators.get(type(node.op))
            if not op:
                raise ValueError(f"{node.op}")
            return op(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = cls._eval_node(node.operand)
            return cls._operators[type(node.op)](operand)
        else:
            raise ValueError(f"{type(node)}")

    @classmethod
    def evaluate(cls, expression: str) -> float:
        try:
            tree = ast.parse(expression, mode='eval')
            return cls._eval_node(tree.body)
        except ZeroDivisionError:
            raise HTTPException(status_code=400, detail="Деление на ноль")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Некорректное выражение: {str(e)}")


class Operation(BaseModel):
    a: float
    op: str
    b: float

class ExpressionRequest(BaseModel):
    expression: str


current_expression: Optional[str] = None


# Простые операции
@app.post("/calc/simple")
def simple_calc(op: Operation):
    if op.op == "+":
        result = op.a + op.b
    elif op.op == "-":
        result = op.a - op.b
    elif op.op == "*":
        result = op.a * op.b
    elif op.op == "/":
        if op.b == 0:
            raise HTTPException(status_code=400, detail="Деление на ноль")
        result = op.a / op.b
    else:
        raise HTTPException(status_code=400, detail="Неподдерживаемая операция")
    return {"result": result}


# Сложное выражение (строка)
@app.post("/calc/expression")
def calc_expression(req: ExpressionRequest):
    global current_expression
    current_expression = req.expression
    try:
        result = SafeEval.evaluate(req.expression)
        return {"expression": req.expression, "result": result}
    except HTTPException:
        raise
    except:
        raise HTTPException(status_code=400, detail="Ошибка при вычислении")


# Просмотр текущего выражения
@app.get("/calc/current")
def get_current_expression():
    if current_expression is None:
        return {"expression": "Нет текущего выражения"}
    return {"expression": current_expression}


# Выполнение текущего выражения
@app.post("/calc/evaluate")
def evaluate_current():
    if current_expression is None:
        raise HTTPException(status_code=400, detail="Нет выражения для вычисления")
    try:
        result = SafeEval.evaluate(current_expression)
        return {"expression": current_expression, "result": result}
    except HTTPException:
        raise
    except:
        raise HTTPException(status_code=400, detail="Ошибка при вычислении")

@app.delete("/calc/clear")
def clear_expression():
    global current_expression
    current_expression = None
    return {"status": "Выражение очищено"}