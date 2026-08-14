import os
import sys

# Os modulos importam matplotlib.pyplot no topo; sem backend headless o import
# falha em ambiente sem display (WSL, CI).
os.environ.setdefault("MPLBACKEND", "Agg")

# Permite importar os modulos da raiz do projeto.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
