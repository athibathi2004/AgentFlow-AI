"""Safe Mathematical Calculator Tool with AST parser."""

import ast
import math
import operator
from typing import Any, Dict
from pydantic import BaseModel, Field
from app.core.exceptions import ToolExecutionError
from app.tools.base import BaseTool


class CalculatorInput(BaseModel):
    expression: str = Field(
        ...,
        description="Mathematical expression to evaluate safely (e.g. '120 * (1 - 0.25)' or 'sqrt(144) + 15')",
        examples=["100 * 1.15", "sqrt(64) + 42", "round(10 / 3, 2)"],
    )


class SafeMathEvaluator(ast.NodeVisitor):
    """AST NodeVisitor that safely evaluates arithmetic operations without eval()."""

    ALLOWED_OPERATORS = {
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

    ALLOWED_FUNCTIONS = {
        "abs": abs,
        "round": round,
        "sqrt": math.sqrt,
        "pow": math.pow,
        "min": min,
        "max": max,
        "ceil": math.ceil,
        "floor": math.floor,
        "log": math.log,
        "exp": math.exp,
    }

    ALLOWED_CONSTANTS = {
        "pi": math.pi,
        "e": math.e,
    }

    def visit(self, node: ast.AST) -> Any:
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ast.AST) -> Any:
        raise ToolExecutionError(
            f"Unsupported mathematical syntax or operation: {node.__class__.__name__}"
        )

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node.value, (int, float)):
            return node.value
        raise ToolExecutionError(f"Unsupported constant type: {type(node.value)}")

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_type = type(node.op)
        if op_type not in self.ALLOWED_OPERATORS:
            raise ToolExecutionError(f"Unsupported binary operator: {op_type.__name__}")
        try:
            return self.ALLOWED_OPERATORS[op_type](left, right)
        except ZeroDivisionError:
            raise ToolExecutionError("Division by zero in mathematical expression")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        operand = self.visit(node.operand)
        op_type = type(node.op)
        if op_type not in self.ALLOWED_OPERATORS:
            raise ToolExecutionError(f"Unsupported unary operator: {op_type.__name__}")
        return self.ALLOWED_OPERATORS[op_type](operand)

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name):
            raise ToolExecutionError("Dynamic function invocation is not permitted")
        func_name = node.func.id
        if func_name not in self.ALLOWED_FUNCTIONS:
            raise ToolExecutionError(
                f"Function '{func_name}' is not in the approved mathematical whitelist"
            )
        args = [self.visit(arg) for arg in node.args]
        return self.ALLOWED_FUNCTIONS[func_name](*args)

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id in self.ALLOWED_CONSTANTS:
            return self.ALLOWED_CONSTANTS[node.id]
        raise ToolExecutionError(f"Unknown variable or identifier '{node.id}' in expression")


class CalculatorTool(BaseTool):
    """Tool for safe, sandboxed mathematical evaluation."""

    id = "calculator"
    name = "Safe Mathematical Calculator"
    description = (
        "Safely evaluates mathematical expressions, statistical summaries, "
        "and numerical formulas using AST parsing without unrestricted code execution."
    )
    parameters_schema = CalculatorInput
    is_sensitive = False
    requires_approval = False

    async def run(self, expression: str) -> Dict[str, Any]:
        # Normalize ^ to **
        normalized = expression.replace("^", "**").strip()
        try:
            parsed = ast.parse(normalized, mode="eval")
            evaluator = SafeMathEvaluator()
            result_val = evaluator.visit(parsed)
            # Round float nicely if close to int or long decimals
            if isinstance(result_val, float) and result_val.is_integer():
                formatted = int(result_val)
            elif isinstance(result_val, float):
                formatted = round(result_val, 6)
            else:
                formatted = result_val

            return {
                "expression": expression,
                "value": formatted,
                "type": type(formatted).__name__,
            }
        except SyntaxError as se:
            raise ToolExecutionError(f"Syntax error in expression: {str(se)}")

