import pytest

from analise_bateria import ModeloBateria, simular_descarga


def test_descarga_reduz_soc_sem_sair_dos_limites():
    bateria = ModeloBateria()
    anterior = bateria.soc

    for _ in range(10):
        resultado = bateria.descarga_step(corrente=0.5, dt=1.0)
        assert 0 <= resultado["SOC"] <= 1
        assert resultado["SOC"] < anterior
        anterior = resultado["SOC"]


def test_cutoff_interrompe_descarga():
    bateria = ModeloBateria(V_cutoff=4.0)

    assert bateria.descarga_step(corrente=0.5, dt=1.0) is None
    assert bateria.soc == 1.0


@pytest.mark.parametrize(
    "corrente,dt",
    [(-0.1, 1.0), (0.5, 0), (0.5, -1)],
)
def test_descarga_rejeita_entrada_fisicamente_invalida(corrente, dt):
    with pytest.raises(ValueError):
        ModeloBateria().descarga_step(corrente, dt)


def test_simulacao_retorna_series_alinhadas():
    resultado = simular_descarga(lambda _t: 0.5, dt=1.0, tempo_maximo=5.0)

    assert len(resultado["tempo"]) == 6
    assert len(resultado["tempo"]) == len(resultado["tensao"])
    assert len(resultado["tempo"]) == len(resultado["corrente"])
    assert len(resultado["tempo"]) == len(resultado["soc"])
