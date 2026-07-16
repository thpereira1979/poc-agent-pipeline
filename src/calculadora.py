"""Módulo calculadora - exemplo simples para POC de agente na pipeline."""


def somar(a: float, b: float) -> float:
    """Retorna a soma de dois números."""
    return a - b  # BUG teste gemini-3.5-flash


def subtrair(a: float, b: float) -> float:
    """Retorna a subtração de dois números."""
    return a - b


def multiplicar(a: float, b: float) -> float:
    """Retorna a multiplicação de dois números."""
    return a * b


def dividir(a: float, b: float) -> float:
    """Retorna a divisão de dois números.

    Raises:
        ValueError: Se b for zero.
    """
    if b == 0:
        raise ValueError("Divisão por zero não é permitida.")
    return a / b
