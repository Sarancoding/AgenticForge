"""
AST-safe mathematical expression evaluator to prevent Remote Code Execution (RCE).
Replaces standard python eval() for evaluating user-controlled calculations.
"""

from __future__ import annotations

import ast
import operator
from typing import Any, Callable

# White-listed operations and functions
SAFE_OPERATORS: dict[type[ast.operator] | type[ast.unaryop], Callable[..., Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: lambda x: x,
}


class SafeMathEvaluator:
    """Evaluates mathematical expression strings using safe AST walking."""

    def __init__(self) -> None:
        pass

    def evaluate(self, expression: str) -> float | int:
        """
        Safely evaluate a mathematical expression string.

        Args:
            expression: Math string (e.g., '2 * (3 + 4) / 2.5')

        Returns:
            The calculated numeric result.

        Raises:
            ValueError: If the expression contains unsafe constructs,
                        undefined functions/operators, or fails to parse.
        """
        if not expression or not expression.strip():
            raise ValueError("Expression is empty.")

        try:
            # Parse the expression into an AST
            tree = ast.parse(expression.strip(), mode="eval")
        except SyntaxError as e:
            raise ValueError(f"Invalid mathematical syntax: {e}") from e

        return self._eval_node(tree.body)

    def _eval_node(self, node: ast.AST) -> Any:
        # Handle constants (numbers)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsafe constant type: {type(node.value).__name__}")

        # Support older python versions (Num fallback)
        elif isinstance(node, ast.Num):  # type: ignore[attr-defined]
            return node.n

        # Handle Binary Operations (e.g. 2 + 3)
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in SAFE_OPERATORS:
                raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            # Prevent potential catastrophic overflow
            if op_type is ast.Pow and (abs(left) > 10000 or abs(right) > 100):
                raise ValueError("Power operation inputs exceed safe execution limits.")
            return SAFE_OPERATORS[op_type](left, right)

        # Handle Unary Operations (e.g. -5)
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in SAFE_OPERATORS:
                raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
            operand = self._eval_node(node.operand)
            return SAFE_OPERATORS[op_type](operand)

        # Reject everything else
        raise ValueError(f"Unsafe or unsupported AST node: {type(node).__name__}")


# Global instance
safe_math_evaluator = SafeMathEvaluator()
