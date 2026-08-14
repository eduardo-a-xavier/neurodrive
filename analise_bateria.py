"""Modelo simples de descarga da bateria do carrinho Kizumba 4x4."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


BATERIA = {
    "voltagem_nominal": 3.7,
    "energia_total": 1.85,
    "capacidade_mah": 500,
    "resistencia_interna": 0.5,
}

PASTA_GRAFICOS = Path(__file__).resolve().parent / "web" / "assets" / "simulations"


class ModeloBateria:
    """Modelo LiPo com descarga por carga acumulada e queda resistiva."""

    def __init__(self, V_nom=3.7, E_total=1.85, R_int=0.5, V_cutoff=2.5):
        if V_nom <= 0 or E_total <= 0:
            raise ValueError("tensão e energia devem ser positivas")
        if R_int < 0 or V_cutoff < 0:
            raise ValueError("resistência e cutoff não podem ser negativos")

        self.V_nom = V_nom
        self.E_total = E_total
        self.R_int = R_int
        self.V_cutoff = V_cutoff
        self.Q_total = (E_total / V_nom) * 3600
        self.Q_discharged = 0.0

    @property
    def soc(self):
        return max(0.0, min(1.0, 1 - self.Q_discharged / self.Q_total))

    def voltagem(self, corrente):
        """Retorna tensão terminal e tensão de circuito aberto."""
        V_oc = 3.0 + (4.2 - 3.0) * self.soc
        return V_oc - self.R_int * corrente, V_oc

    def descarga_step(self, corrente, dt):
        """Avança a descarga; retorna ``None`` ao atingir vazio ou cutoff."""
        if corrente < 0 or dt <= 0:
            raise ValueError("corrente deve ser não negativa e dt deve ser positivo")
        if self.Q_discharged >= self.Q_total:
            return None

        V_terminal, _ = self.voltagem(corrente)
        if V_terminal <= self.V_cutoff:
            return None

        self.Q_discharged = min(
            self.Q_total,
            self.Q_discharged + corrente * dt,
        )
        V_terminal, V_oc = self.voltagem(corrente)
        return {
            "V_terminal": V_terminal,
            "V_oc": V_oc,
            "energia": V_terminal * corrente * dt / 3600,
            "SOC": self.soc,
        }


def simular_descarga(corrente_por_tempo, dt=0.1, tempo_maximo=3600):
    """Simula uma bateria nova para uma função ``corrente_por_tempo(t)``."""
    bateria = ModeloBateria()
    tempo = []
    tensao = []
    corrente = []
    soc = []
    energia_total = 0.0
    instante = 0.0

    while instante <= tempo_maximo:
        corrente_atual = corrente_por_tempo(instante)
        resultado = bateria.descarga_step(corrente_atual, dt)
        if resultado is None:
            break
        tempo.append(instante)
        tensao.append(resultado["V_terminal"])
        corrente.append(corrente_atual)
        soc.append(resultado["SOC"])
        energia_total += resultado["energia"]
        instante += dt

    return {
        "tempo": np.asarray(tempo),
        "tensao": np.asarray(tensao),
        "corrente": np.asarray(corrente),
        "soc": np.asarray(soc),
        "energia_total": energia_total,
    }


def gerar_cenarios():
    constante = simular_descarga(lambda _t: 0.5)
    variavel = simular_descarga(lambda t: 0.8 if t < 1.0 else 0.3)
    return constante, variavel


def plotar_analise_bateria(caminho=None):
    """Gera o gráfico usado pelo dashboard e retorna seu caminho."""
    constante, variavel = gerar_cenarios()
    fig, axes = plt.subplots(2, 2, figsize=(13, 10))

    axes[0, 0].plot(constante["tempo"] / 60, constante["tensao"], "b-", linewidth=2)
    axes[0, 0].axhline(BATERIA["voltagem_nominal"], color="g", linestyle="--")
    axes[0, 0].axhline(2.5, color="r", linestyle="--")
    axes[0, 0].set_title("Descarga com corrente constante (0,5 A)")
    axes[0, 0].set_ylabel("Tensão [V]")
    axes[0, 0].grid(True, alpha=0.3)

    axes[0, 1].plot(constante["tempo"] / 60, constante["soc"] * 100, "g-")
    axes[0, 1].set_title("Nível de carga — corrente constante")
    axes[0, 1].set_ylabel("Carga [%]")
    axes[0, 1].set_ylim(0, 105)
    axes[0, 1].grid(True, alpha=0.3)

    ax_corrente = axes[1, 0]
    ax_tensao = ax_corrente.twinx()
    ax_corrente.plot(variavel["tempo"] / 60, variavel["corrente"], "r-")
    ax_tensao.plot(variavel["tempo"] / 60, variavel["tensao"], "b-")
    ax_corrente.set_title("Aceleração e regime constante")
    ax_corrente.set_xlabel("Tempo [min]")
    ax_corrente.set_ylabel("Corrente [A]", color="r")
    ax_tensao.set_ylabel("Tensão [V]", color="b")
    ax_corrente.grid(True, alpha=0.3)

    axes[1, 1].plot(variavel["tempo"] / 60, variavel["soc"] * 100, "g-")
    axes[1, 1].set_title("Nível de carga — cenário variável")
    axes[1, 1].set_xlabel("Tempo [min]")
    axes[1, 1].set_ylabel("Carga [%]")
    axes[1, 1].set_ylim(0, 105)
    axes[1, 1].grid(True, alpha=0.3)

    destino = Path(caminho) if caminho else PASTA_GRAFICOS / "analise_bateria.png"
    destino.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(destino, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return destino


def imprimir_resumo():
    capacidade_ah = BATERIA["capacidade_mah"] / 1000
    constante, variavel = gerar_cenarios()
    print("ANÁLISE DE BATERIA — CARRINHO KIZUMBA 4X4")
    print(f"Capacidade: {capacidade_ah:.2f} Ah")
    print(f"Cenário 0,5 A: {constante['tempo'][-1] / 60:.1f} min")
    print(f"Cenário variável: {variavel['tempo'][-1] / 60:.1f} min")


if __name__ == "__main__":
    imprimir_resumo()
    print(f"Gráfico salvo: {plotar_analise_bateria()}")
