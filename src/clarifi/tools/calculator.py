"""Safe math calculator — lets the agent compute exact results instead of guessing.

Evaluates Python math expressions in a restricted namespace.
Only arithmetic operators and common math functions are available.
"""

import math

from langchain_core.tools import tool

# Restricted namespace — only math, no imports, no builtins
_SAFE_GLOBALS = {"__builtins__": {}}
_SAFE_LOCALS = {
    # Basic math functions
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "len": len,
    "int": int,
    "float": float,
    # Math module functions
    "ceil": math.ceil,
    "floor": math.floor,
    "sqrt": math.sqrt,
    "pow": pow,
    "log": math.log,
    "log10": math.log10,
    # Constants
    "pi": math.pi,
}


@tool
async def calculate(expression: str) -> dict:
    """Evalueaza o expresie matematica si returneaza rezultatul exact.

    Foloseste pentru calcule precise — NU calcula in cap!

    Exemple:
      calculate("44149 + 76398")             => 120547
      calculate("29000 - 8000 + 70000")      => 91000
      calculate("55000 / 70000 * 100")       => 78.57 (procent)
      calculate("round(44149 * 0.19, 2)")    => 8388.31
      calculate("sum([30000, 25000, 15000])") => 70000
      calculate("82776.80 - 47250")          => 35526.80

    Operatori: + - * / // % **
    Functii: abs, round, min, max, sum, len, ceil, floor, sqrt, pow, log
    """
    try:
        # Block attribute access and dunder exploits
        if "__" in expression or "import" in expression or "exec" in expression:
            return {
                "error": "Expresie nepermisa",
                "hint": "Foloseste doar numere, operatori si functii matematice",
            }

        code = compile(expression, "<calc>", "eval")

        # Block dangerous names
        for name in code.co_names:
            if name not in _SAFE_LOCALS and name not in (
                "True", "False", "None",
            ):
                return {
                    "error": f"Functie necunoscuta: {name}",
                    "hint": "Functii disponibile: abs, round, min, max, "
                            "sum, ceil, floor, sqrt, pow, log",
                }

        result = eval(code, _SAFE_GLOBALS, _SAFE_LOCALS)  # noqa: S307
        return {"expression": expression, "result": result}

    except SyntaxError:
        return {"error": f"Sintaxa invalida: {expression}"}
    except ZeroDivisionError:
        return {"error": "Impartire la zero"}
    except Exception as e:
        return {"error": str(e)}
