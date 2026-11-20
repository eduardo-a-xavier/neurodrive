"""Testes do controlador PWM.

Referencia fisica: V_med = V_max * D; I_med = V_med / R; P = V_med * I_med.
O ripple de corrente e uma amplitude pico-a-pico: nunca negativo.
"""

import pytest

from pwm_analise import ControladorPWM

V_MAX = 3.7
R = 3.0


@pytest.fixture
def pwm():
    return ControladorPWM(V_max=V_MAX, f_pwm=5000, R_motor=R, L_motor=0.0005, K_e=0.02)


@pytest.mark.parametrize(
    "duty,esperado",
    [(0, 0.0), (25, 0.25 * V_MAX), (50, 0.5 * V_MAX), (100, V_MAX)],
)
def test_tensao_media_e_linear_no_duty(pwm, duty, esperado):
    assert pwm.tensao_media_pwm(duty) == pytest.approx(esperado)


def test_corrente_media_segue_a_lei_de_ohm(pwm):
    assert pwm.corrente_media_esperada(50) == pytest.approx(0.5 * V_MAX / R)


def test_potencia_media_cresce_com_o_quadrado_do_duty(pwm):
    """P = V_med^2 / R, entao dobrar o duty quadruplica a potencia."""
    assert pwm.potencia_media(50) == pytest.approx(4 * pwm.potencia_media(25))


def test_periodo_e_o_inverso_da_frequencia(pwm):
    assert pwm.T_pwm == pytest.approx(1 / 5000)


def test_ripple_zero_quando_indutancia_zero():
    """Guarda explicita do codigo: L == 0 retorna 0 em vez de dividir por zero."""
    sem_indutancia = ControladorPWM(V_max=V_MAX, R_motor=R, L_motor=0.0)
    assert sem_indutancia.ripple_corrente(50) == 0


def test_ripple_maximo_no_meio_do_duty(pwm):
    """Com o motor parado, o ripple e maximo perto de D=50% e nulo nos extremos."""
    meio = pwm.ripple_corrente(50, omega=0)
    assert meio > pwm.ripple_corrente(5, omega=0)
    assert meio > pwm.ripple_corrente(95, omega=0)


@pytest.mark.parametrize("duty", [0, 10, 25, 50, 75, 90, 100])
def test_ripple_nunca_e_negativo_com_motor_girando(pwm, duty):
    """Ripple e uma amplitude e nao depende do sinal da BEMF."""
    assert pwm.ripple_corrente(duty, omega=100) >= 0


def test_ripple_e_zero_nos_extremos(pwm):
    assert pwm.ripple_corrente(0) == 0
    assert pwm.ripple_corrente(100) == pytest.approx(0)
