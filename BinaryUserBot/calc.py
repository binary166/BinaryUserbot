"""
Безопасный математический калькулятор.
"""
import math

SAFE_NS = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
SAFE_NS.update({"abs": abs, "round": round, "int": int, "float": float})


def safe_calc(expr: str) -> str:
    expr = expr.replace("^", "**").strip()
    try:
        result = eval(expr, {"__builtins__": {}}, SAFE_NS)
        return f"{result:.10g}" if isinstance(result, float) else str(result)
    except ZeroDivisionError:
        return "∞ (деление на ноль)"
    except Exception as e:
        return f"Ошибка: {e}"
