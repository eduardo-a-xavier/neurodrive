"""Testes do modelo de motor DC.

Referencia fisica: P_mec = K_t*I*omega, P_elec = V*I, eficiencia = P_mec/P_elec
e deve ficar em [0, 1].
"""

import warnings

import numpy as np
import pytest

from motor_simulation import MotorDC


@pytest.fixture
def motor():
    return MotorDC()


def test_potencia_eletrica_e_v_vezes_i(motor):
    assert motor.potencia_eletrica(3.7, 0.5) == pytest.approx(3.7 * 0.5)


def test_potencia_mecanica_proporcional_a_corrente_e_velocidade(motor):
    dobro = motor.potencia_mecanica(corrente=1.0, omega=200)
    simples = motor.potencia_mecanica(corrente=0.5, omega=200)
    assert dobro == pytest.approx(2 * simples)


def test_potencia_mecanica_nula_com_motor_parado(motor):
    assert motor.potencia_mecanica(corrente=1.0, omega=0) == 0


def test_atrito_nao_cria_salto_perto_de_velocidade_zero(motor):
    voltagem_zero = lambda _t: 0.0
    derivada_negativa = motor.sistema([0.0, -1e-6], 0.0, voltagem_zero)[1]
    derivada_positiva = motor.sistema([0.0, 1e-6], 0.0, voltagem_zero)[1]

    assert derivada_negativa > 0
    assert derivada_positiva < 0
    assert abs(derivada_negativa) == pytest.approx(abs(derivada_positiva))


def test_eficiencia_zero_quando_potencia_eletrica_desprezivel(motor):
    """Guarda do codigo: p_elec <= 0.01 retorna 0."""
    assert motor.eficiencia(voltagem=0.0, corrente=0.0, omega=0.0) == 0


@pytest.mark.parametrize("corrente", [0.1, 0.3, 0.5, 0.8])
def test_eficiencia_dentro_de_zero_e_um(motor, corrente):
    """Sanidade fisica: o motor nao entrega mais potencia do que consome.

    O ponto de operacao precisa ser coerente: em regime estacionario
    V = I*R + K_e*omega. Passar (V, I, omega) independentes descreve um motor
    que nao existe -- com V=3.7, I=0.5 e omega=300 a funcao devolve 162%, mas
    essa combinacao e impossivel (a forca contra-eletromotriz superaria a fonte).
    """
    voltagem = 3.7
    omega = (voltagem - corrente * motor.R) / motor.K_e

    eta = motor.eficiencia(voltagem, corrente, omega)
    assert 0.0 <= eta <= 1.0


def test_eficiencia_nao_emite_warning_de_divisao_por_zero(motor):
    """Potencia zero e tratada antes da divisao vetorial."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        motor.eficiencia(
            voltagem=np.array([3.7, 0.0]),
            corrente=np.array([0.5, 0.0]),
            omega=np.array([300.0, 0.0]),
        )
