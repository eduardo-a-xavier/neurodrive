"""Testes da analise de frequencia (FFT, picos, THD).

Estes testes usam sinais sinteticos com resposta analitica conhecida: e o que
torna esta parte do projeto barata de testar.
"""

import numpy as np
import pytest

from analise_frequencia import AnalisadorFrequencia

FS = 10000
F0 = 50.0


@pytest.fixture
def an():
    return AnalisadorFrequencia(frequencia_amostragem=FS)


def senoide(freq, amplitude=1.0, duracao=0.2, fs=FS):
    t = np.arange(0, duracao, 1 / fs)
    return t, amplitude * np.sin(2 * np.pi * freq * t)


def test_fft_encontra_a_frequencia_da_senoide(an):
    t, sinal = senoide(F0)
    freqs, magnitude, _ = an.calcular_fft(sinal, t)

    pico = freqs[np.argmax(magnitude)]
    assert pico == pytest.approx(F0, abs=5.0)


def test_fft_devolve_apenas_frequencias_positivas(an):
    t, sinal = senoide(F0)
    freqs, magnitude, fase = an.calcular_fft(sinal, t)

    assert np.all(freqs >= 0)
    assert len(freqs) == len(magnitude) == len(fase)


def test_thd_de_senoide_pura_e_quase_zero(an):
    """Sinal sem harmonicas: THD deve ser proximo de 0%."""
    t, sinal = senoide(F0)
    freqs, magnitude, _ = an.calcular_fft(sinal, t)

    assert an.calcular_thd(freqs, magnitude, F0) < 1.0


def test_thd_com_terceira_harmonica_conhecida(an):
    """Fundamental 1 + terceira harmonica 0,1 tem THD de 10%."""
    t, fundamental = senoide(F0)
    _, harmonica = senoide(3 * F0, amplitude=0.1)
    freqs, magnitude, _ = an.calcular_fft(fundamental + harmonica, t)

    assert an.calcular_thd(freqs, magnitude, F0) == pytest.approx(10.0, rel=0.05)


def test_thd_zero_quando_nao_ha_fundamental(an):
    """Guarda explicita do codigo: I_1 < 1e-6 retorna 0."""
    freqs = np.linspace(0, 500, 100)
    magnitude = np.zeros_like(freqs)

    assert an.calcular_thd(freqs, magnitude, F0) == 0


def test_encontrar_picos_ordena_do_maior_para_o_menor(an):
    t, forte = senoide(F0, amplitude=1.0)
    _, fraco = senoide(5 * F0, amplitude=0.3)
    freqs, magnitude, _ = an.calcular_fft(forte + fraco, t)

    picos_freq, picos_mag, _ = an.encontrar_picos(freqs, magnitude, num_picos=2)

    assert picos_mag[0] >= picos_mag[1]
    assert picos_freq[0] == pytest.approx(F0, abs=5.0)


def test_encontrar_picos_com_sinal_silencioso(an):
    """Um sinal silencioso devolve listas vazias sem warning nem NaN."""
    freqs = np.linspace(0, 500, 100)
    magnitude = np.zeros_like(freqs)

    with np.errstate(invalid="raise", divide="raise"):
        picos_freq, picos_mag, _ = an.encontrar_picos(freqs, magnitude)

    assert len(picos_freq) == len(picos_mag) == 0
    assert not np.any(np.isnan(picos_mag))
