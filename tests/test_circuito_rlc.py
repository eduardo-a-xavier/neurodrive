"""Testes do circuito RLC serie.

Referencia fisica: para um RLC serie, omega_0 = 1/sqrt(LC) e
zeta = R / (2*sqrt(L/C)). zeta < 1 sub-amortecido, zeta == 1 critico,
zeta > 1 sobre-amortecido.
"""

import math

import pytest

from circuito_rlc import CircuitoRLC

L = 0.0005
C = 100e-6
R_CRITICO = 2 * math.sqrt(L / C)


def test_omega_0_bate_com_a_formula():
    c = CircuitoRLC(R=3.0, L=L, C=C)
    assert c.omega_0 == pytest.approx(1 / math.sqrt(L * C))
    assert c.f_0 == pytest.approx(c.omega_0 / (2 * math.pi))


def test_sub_amortecido_quando_R_abaixo_do_critico():
    c = CircuitoRLC(R=R_CRITICO / 2, L=L, C=C)
    assert c.zeta < 1
    assert "Sub-amortecida" in c.tipo_resposta()


def test_sobre_amortecido_quando_R_acima_do_critico():
    c = CircuitoRLC(R=R_CRITICO * 2, L=L, C=C)
    assert c.zeta > 1
    assert "Sobre-amortecida" in c.tipo_resposta()


def test_omega_d_so_existe_no_sub_amortecido():
    sub = CircuitoRLC(R=R_CRITICO / 2, L=L, C=C)
    sobre = CircuitoRLC(R=R_CRITICO * 2, L=L, C=C)

    assert sub.omega_d is not None
    assert sub.omega_d < sub.omega_0  # amortecimento sempre reduz a frequencia
    assert sobre.omega_d is None
    assert sobre.f_d is None


def test_critico_quando_R_vem_do_mesmo_caminho_de_calculo():
    """Caso feliz: R derivado da mesma expressao cai exatamente em zeta == 1."""
    c = CircuitoRLC(R=R_CRITICO, L=L, C=C)
    assert c.zeta == 1.0
    assert "Criticamente" in c.tipo_resposta()


def test_critico_com_R_arredondado():
    """Um valor critico medido continua critico dentro da tolerancia."""
    R_medido = round(R_CRITICO, 7)  # 4.4721360 — precisao de multimetro
    c = CircuitoRLC(R=R_medido, L=L, C=C)

    assert c.zeta == pytest.approx(1.0, rel=1e-6), "deveria ser critico na pratica"
    assert "Criticamente" in c.tipo_resposta()


@pytest.mark.parametrize(
    "Lv,Cv",
    [(1e-4, 1e-6), (5e-4, 22e-6), (1e-3, 470e-6), (2.2e-3, 100e-6)],
)
def test_critico_para_varios_pares_LC(Lv, Cv):
    """Caminhos algebricamente equivalentes preservam a classificacao."""
    R = 2 * math.sqrt(Lv) / math.sqrt(Cv)  # equivalente a 2*sqrt(L/C)
    c = CircuitoRLC(R=R, L=Lv, C=Cv)

    assert "Criticamente" in c.tipo_resposta()
