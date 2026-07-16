"""Testes unitários para o módulo calculadora."""

import pytest
from src.calculadora import somar, subtrair, multiplicar, dividir


class TestSomar:
    def test_soma_positivos(self):
        assert somar(2, 3) == 5

    def test_soma_negativos(self):
        assert somar(-1, -1) == -2

    def test_soma_zero(self):
        assert somar(0, 0) == 0


class TestSubtrair:
    def test_subtracao_simples(self):
        assert subtrair(10, 3) == 7

    def test_subtracao_resultado_negativo(self):
        assert subtrair(3, 10) == -7


class TestMultiplicar:
    def test_multiplicacao_positivos(self):
        assert multiplicar(4, 5) == 20

    def test_multiplicacao_por_zero(self):
        assert multiplicar(100, 0) == 0


class TestDividir:
    def test_divisao_simples(self):
        assert dividir(10, 2) == 5.0

    def test_divisao_decimal(self):
        assert dividir(7, 2) == 3.5

    def test_divisao_por_zero(self):
        with pytest.raises(ValueError, match="Divisão por zero"):
            dividir(10, 0)
