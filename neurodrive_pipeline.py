import cv2
import numpy as np
import time
import math
import os
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv

load_dotenv()
SENSOR_SERVER_PORT = int(os.getenv("SENSOR_SERVER_PORT", "8000"))

# Variaveis globais para telemetria externa (Sensor Logger)
telemetria_ext = {
    "aceleracao_x": 0.0,
    "aceleracao_y": 0.0,
    "aceleracao_z": 0.0,
    "gps_speed_ms": 0.0,
    "ultima_att": 0.0
}

class SensorLoggerHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                payload = data.get("payload", [])
                for p in payload:
                    name = p.get("name")
                    vals = p.get("values", {})
                    if name == "accelerometer" or name == "gravity":
                        telemetria_ext["aceleracao_x"] = vals.get("x", 0.0)
                        telemetria_ext["aceleracao_y"] = vals.get("y", 0.0)
                        telemetria_ext["aceleracao_z"] = vals.get("z", 0.0)
                        telemetria_ext["ultima_att"] = time.time()
                    elif name == "location":
                        telemetria_ext["gps_speed_ms"] = vals.get("speed", 0.0)
                        telemetria_ext["ultima_att"] = time.time()
            except Exception:
                pass
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass # Silencia logs para nao poluir o terminal

def iniciar_servidor_sensores():
    server = HTTPServer(('0.0.0.0', SENSOR_SERVER_PORT), SensorLoggerHandler)
    server.serve_forever()

threading.Thread(target=iniciar_servidor_sensores, daemon=True).start()

# ==============================================================================
#  NEURODRIVE OS v3.0 - Calibração de 1 Metro + Fallback Simulado
# ==============================================================================
#
#  TECLAS DURANTE A EXECUÇÃO:
#  [C] - Inicia/Para a calibração de 1 metro (calcula fator_px_mm automaticamente)
#  [S] - Alterna entre modo REAL (optical flow calibrado) e SIMULADO (30km/h máx)
#  [R] - Reseta estatísticas (média, máxima, histórico)
#  [Q] - Sai do programa
#
#  COMO CALIBRAR (recomendado):
#  1. Marque 1 metro no chão (ex: fita adesiva em 0cm e 100cm)
#  2. Posicione o carrinho na marca de 0 cm
#  3. Pressione [C] para iniciar
#  4. Mova o carrinho até a marca de 1 metro em velocidade constante
#  5. Pressione [C] novamente — o fator é calculado e salvo automaticamente
#
#  COMO FUNCIONA O MODO SIMULADO:
#  - Mapeia o optical flow relativo (0% a 100% do máximo observado)
#  - Para a velocidade real do carrinho (0 a 30 km/h)
#  - O "máximo observado" é auto-aprendido ao longo do uso e salvo em disco
# ==============================================================================

ARQUIVO_CALIBRACAO   = "calibracao_neurodrive.json"
VEL_MAX_CARRINHO_KMH = 30.0   # Velocidade máxima real do carrinho (spec fabricante)
ESCALA_MAQUETE       = 30.0   # Escala 1:30 (escala real medida)


class OdometriaVisual:
    def __init__(self, escala=ESCALA_MAQUETE):
        self.frame_cinza_anterior  = None
        self.pontos_rastreados     = None
        self.ultimo_tempo          = time.time()

        # Física / velocidade
        self.velocidade_instantanea_kmh = 0.0
        self.velocidade_media_kmh       = 0.0
        self.aceleracao_ms2             = 0.0
        self.velocidade_maxima          = 0.0
        self.qualidade_rastreio         = 0

        # Históricos
        self.historico_recente     = []
        self.historico_grafico     = []
        self.soma_velocidades_curso = 0.0
        self.qtd_medicoes_curso    = 0

        self.escala = escala

        # Calibração — carrega do disco se existir
        self.fator_px_mm                = None
        self.flow_maximo_observado_pxs  = None
        self._carregar_calibracao()

        # Estado da calibração interativa
        self.calibrando              = False
        self.calib_pixels_acumulados = 0.0
        self.calib_frames            = 0
        self.calib_tempo_inicio      = 0.0

        # Variaveis para o modo LISTRAS
        self.distancia_listras_m = 1.0
        self.ultimo_tempo_listra = None
        self.faixa_passando      = False

        # Modo de operação e Layout
        self.modo = "real" if self.fator_px_mm is not None else "simulado"
        self.layout = "velocimetro"
        self.tempo_demo = 0.0

        print(f"\n[NEURODRIVE] Iniciando — modo: {self.modo.upper()}")
        if self.fator_px_mm:
            print(f"[NEURODRIVE] Calibração: 1 px = {self.fator_px_mm:.4f} mm real")
        else:
            print("[NEURODRIVE] Sem calibração. Pressione [C] para calibrar ou [S] para modo simulado.")

    # ──────────────────────────────────────────────────────────────────
    #  PERSISTÊNCIA EM DISCO
    # ──────────────────────────────────────────────────────────────────
    def _carregar_calibracao(self):
        if os.path.exists(ARQUIVO_CALIBRACAO):
            try:
                with open(ARQUIVO_CALIBRACAO) as f:
                    d = json.load(f)
                self.fator_px_mm               = d.get("fator_px_mm")
                self.flow_maximo_observado_pxs = d.get("flow_maximo_pxs")
                if self.fator_px_mm:
                    print(f"[CALIB] Carregado: fator_px_mm = {self.fator_px_mm:.4f}")
            except Exception as e:
                print(f"[CALIB] Erro ao carregar: {e}")

    def _salvar_calibracao(self):
        try:
            d = {}
            if os.path.exists(ARQUIVO_CALIBRACAO):
                with open(ARQUIVO_CALIBRACAO) as f:
                    d = json.load(f)
            if self.fator_px_mm is not None:
                d["fator_px_mm"] = self.fator_px_mm
            if self.flow_maximo_observado_pxs is not None:
                d["flow_maximo_pxs"] = self.flow_maximo_observado_pxs
            with open(ARQUIVO_CALIBRACAO, "w") as f:
                json.dump(d, f, indent=2)
        except Exception as e:
            print(f"[CALIB] Erro ao salvar: {e}")

    # ──────────────────────────────────────────────────────────────────
    #  CONTROLE DE TECLAS
    # ──────────────────────────────────────────────────────────────────
    def processar_tecla(self, tecla):
        if tecla in (ord('c'), ord('C')):
            self._toggle_calibracao()
        elif tecla in (ord('s'), ord('S')):
            self._toggle_modo()
        elif tecla in (ord('r'), ord('R')):
            self._resetar_estatisticas()
        elif tecla in (ord('l'), ord('L')):
            self._toggle_layout()

    def _toggle_layout(self):
        if self.layout == "velocimetro":
            self.layout = "cyber"
            print("[LAYOUT] → CYBER (G-Meter & HUD de Combate)")
        else:
            self.layout = "velocimetro"
            print("[LAYOUT] → VELOCIMETRO NEURODRIVE")

    def _toggle_calibracao(self):
        if not self.calibrando:
            self.calibrando              = True
            self.calib_pixels_acumulados = 0.0
            self.calib_frames            = 0
            self.calib_tempo_inicio      = time.time()
            print("\n[CALIB] ► INICIADA. Mova o carrinho 1 metro e pressione [C] novamente.")
        else:
            self.calibrando   = False
            tempo_total       = time.time() - self.calib_tempo_inicio

            if self.calib_pixels_acumulados > 10:
                # 1 metro = 1000 mm reais → fator = 1000 / total_pixels
                self.fator_px_mm = 1000.0 / self.calib_pixels_acumulados
                vel_real_kmh     = (1.0 / tempo_total) * 3.6
                print(f"[CALIB] ✓ Concluída!")
                print(f"[CALIB]   Pixels acumulados : {self.calib_pixels_acumulados:.1f} px")
                print(f"[CALIB]   Tempo total       : {tempo_total:.2f} s")
                print(f"[CALIB]   Vel. real carrinho: {vel_real_kmh:.2f} km/h")
                print(f"[CALIB]   fator_px_mm       : {self.fator_px_mm:.4f}")
                self._salvar_calibracao()
                self.modo = "real"
                print("[CALIB]   Modo alterado para REAL.")
            else:
                print("[CALIB] ✗ Poucos pixels. Descartado — o carrinho se moveu?")

    def _toggle_modo(self):
        if self.modo == "real":
            self.modo = "sensor"
            print("[MODO] → SENSOR CELULAR")
        elif self.modo == "sensor":
            self.modo = "listras"
            print("[MODO] → RASTREIO DE LISTRAS (1m)")
        elif self.modo == "listras":
            self.modo = "demo"
            print("[MODO] → DEMO (Simulador Falso Automático)")
        elif self.modo == "demo":
            self.modo = "simulado"
            print("[MODO] → SIMULADO")
        else:
            if self.fator_px_mm is not None:
                self.modo = "real"
                print(f"[MODO] → REAL (fator={self.fator_px_mm:.4f})")
            else:
                self.modo = "sensor"
                print("[MODO] → SENSOR CELULAR (sem calibração real)")

    def _resetar_estatisticas(self):
        self.velocidade_maxima      = 0.0
        self.velocidade_media_kmh   = 0.0
        self.soma_velocidades_curso = 0.0
        self.qtd_medicoes_curso     = 0
        self.historico_grafico.clear()
        self.historico_recente.clear()
        print("[RESET] Estatísticas zeradas.")

    # ──────────────────────────────────────────────────────────────────
    #  OPTICAL FLOW
    # ──────────────────────────────────────────────────────────────────
    def _extrair_flow(self, frame_cinza_atual, frame_debug):
        h, w = frame_cinza_atual.shape

        # Máscara trapezoidal: exclui capô (25% inferior) e fundo longe (50% superior)
        mascara = np.zeros_like(frame_cinza_atual)
        pts = np.array([[
            [int(w * 0.05), int(h * 0.75)],
            [int(w * 0.25), int(h * 0.50)],
            [int(w * 0.75), int(h * 0.50)],
            [int(w * 0.95), int(h * 0.75)],
        ]], dtype=np.int32)
        cv2.fillPoly(mascara, pts, 255)
        cv2.polylines(frame_debug, pts, True, (0, 255, 255), 1)

        # Inicializa rastreio se necessário
        if self.frame_cinza_anterior is None or \
           self.pontos_rastreados is None or \
           len(self.pontos_rastreados) < 15:
            self.frame_cinza_anterior = frame_cinza_atual
            self.pontos_rastreados = cv2.goodFeaturesToTrack(
                frame_cinza_atual, mask=mascara,
                maxCorners=200, qualityLevel=0.1, minDistance=20, blockSize=7)
            return None, 0

        pontos_novos, status, _ = cv2.calcOpticalFlowPyrLK(
            self.frame_cinza_anterior, frame_cinza_atual,
            self.pontos_rastreados, None,
            winSize=(21, 21), maxLevel=3,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 15, 0.03))

        mediana_px = None
        n_bons     = 0

        if pontos_novos is not None:
            bons_novos    = pontos_novos[status == 1]
            bons_antigos  = self.pontos_rastreados[status == 1]
            n_bons        = len(bons_novos)
            self.qualidade_rastreio = n_bons

            distancias = []
            deslocamentos_y = []
            for novo, antigo in zip(bons_novos, bons_antigos):
                a, b = novo.ravel()
                c, d = antigo.ravel()
                dist = float(np.sqrt((a - c) ** 2 + (b - d) ** 2))
                dy = b - d
                cv2.circle(frame_debug, (int(a), int(b)), 3, (255, 255, 0), -1)
                cv2.line(frame_debug, (int(a), int(b)), (int(c), int(d)), (150, 150, 0), 1)
                if dist < 80:
                    distancias.append(dist)
                    deslocamentos_y.append(dy)

            if distancias:
                mediana_px = float(np.median(distancias))
                mediana_dy = float(np.median(deslocamentos_y))
                # Se os pontos subiram (dy < 0), o carro andou para tras
                if mediana_dy < 0:
                    mediana_px = -mediana_px

            self.frame_cinza_anterior = frame_cinza_atual.copy()
            if n_bons < 40:
                self.pontos_rastreados = cv2.goodFeaturesToTrack(
                    frame_cinza_atual, mask=mascara,
                    maxCorners=200, qualityLevel=0.1, minDistance=20, blockSize=7)
            else:
                self.pontos_rastreados = bons_novos.reshape(-1, 1, 2)

        return mediana_px, n_bons

    # ──────────────────────────────────────────────────────────────────
    #  PAINEL HUD
    # ──────────────────────────────────────────────────────────────────
    def _desenhar_grafico(self, frame, x, y, larg, alt):
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + larg, y + alt), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
        cv2.putText(frame, "HISTORICO (KM/H)", (x + 10, y + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        if len(self.historico_grafico) < 2:
            return
        dados  = [abs(v) for v in self.historico_grafico[-(larg - 20):]]
        max_v  = max(VEL_MAX_CARRINHO_KMH * self.escala, max(dados) if dados else VEL_MAX_CARRINHO_KMH * self.escala)
        
        pts = []
        for i in range(len(dados)):
            xi = x + 10 + i
            yi = y + alt - 10 - int((dados[i] / max_v) * (alt - 40))
            pts.append((xi, yi))
        
        for i in range(1, len(pts)):
            intens = min(255, int((dados[i] / max_v) * 255))
            cv2.line(frame, pts[i-1], pts[i], (255, 255 - intens, intens), 2)

    def desenhar_painel(self, frame):
        H, W = frame.shape[:2]
        
        # Cria uma camada de overlay para os efeitos de transparencia
        overlay = frame.copy()

        # ---------------------------------------------------------
        # BARRA SUPERIOR (Status & Info)
        # ---------------------------------------------------------
        cv2.rectangle(overlay, (0, 0), (W, 40), (0, 0, 0), -1)
        
        # Fundo do Painel de Dados
        dx, dy = W - 280, 50
        cv2.rectangle(overlay, (dx, dy), (dx + 270, dy + 220), (0, 0, 0), -1)

        # Aplica a transparencia do overlay geral
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

        # Textos da barra superior
        cv2.putText(frame, f"NEURODRIVE OS v3.0 | 1:{int(self.escala)}",
                    (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        if self.calibrando:
            cor_badge = (0, 50, 255)
            txt_badge = f">> CALIBRANDO: {self.calib_pixels_acumulados:.0f} px <<"
        elif self.modo == "simulado":
            cor_badge = (255, 255, 255)
            txt_badge = f"MODO SIMULADO | [S]"
        elif self.modo == "sensor":
            cor_badge = (0, 255, 255)
            txt_badge = f"MODO SENSOR CELULAR | [S]"
        elif self.modo == "listras":
            cor_badge = (0, 255, 0)
            txt_badge = f"RASTREIO DE LISTRAS (1m) | [S]"
        elif self.modo == "demo":
            cor_badge = (255, 0, 0)
            txt_badge = f"MODO DEMO (AUTOMATICO) | [S]"
        else:
            cor_badge = (255, 255, 255)
            txt_badge = f"REAL CALIBRADO | [S]"
            
        cv2.putText(frame, txt_badge, (320, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor_badge, 1)

        cor_s  = (255, 255, 0) if self.qualidade_rastreio > 30 else \
                 (0, 165, 255) if self.qualidade_rastreio > 10 else (0, 0, 255)
        txt_s  = "OTIMO" if self.qualidade_rastreio > 30 else \
                 "MEDIO" if self.qualidade_rastreio > 10 else "FRACO"
        cv2.putText(frame, f"SENS: {txt_s} ({self.qualidade_rastreio})",
                    (W - 250, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor_s, 2)

        # ---------------------------------------------------------
        # VELOCIMETRO OU HUD CYBER (G-METER)
        # ---------------------------------------------------------
        if self.layout == "velocimetro":
            cx, cy = 180, H - 150
            raio_ext = 110
            raio_int = 70
            mv = 80  # Maximo de 80 km/h (pois o equivalente atinge cerca de 60-70 km/h)
            
            vd_real = self.velocidade_instantanea_kmh
            vd_abs = abs(vd_real)
            vd = min(vd_abs, mv)
            
            # Fundo do velocimetro circular escuro
            over_vel = frame.copy()
            cv2.circle(over_vel, (cx, cy), raio_ext + 10, (0, 0, 0), -1)
            cv2.addWeighted(over_vel, 0.5, frame, 0.5, 0, frame)
            
            cv2.circle(frame, (cx, cy), raio_ext, (255, 255, 255), 2)
    
            ang_inicio = 150
            ang_fim = 390
            faixa_ang = ang_fim - ang_inicio
            
            for v in range(0, mv + 1, 5):
                prop = v / mv
                ang_deg = ang_inicio + (prop * faixa_ang)
                ang_rad = math.radians(ang_deg)
                
                is_redzone = v >= mv * 0.8
                cor_tick = (255, 0, 255) if is_redzone else (255, 255, 255)
                
                if v % 20 == 0:
                    x1 = int(cx + (raio_ext) * math.cos(ang_rad))
                    y1 = int(cy + (raio_ext) * math.sin(ang_rad))
                    x2 = int(cx + (raio_int) * math.cos(ang_rad))
                    y2 = int(cy + (raio_int) * math.sin(ang_rad))
                    cv2.line(frame, (x1, y1), (x2, y2), cor_tick, 3)
                    
                    xt = int(cx + (raio_int - 20) * math.cos(ang_rad))
                    yt = int(cy + (raio_int - 20) * math.sin(ang_rad))
                    (tw, th), _ = cv2.getTextSize(str(v), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                    cv2.putText(frame, str(v), (xt - tw//2, yt + th//2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor_tick, 1)
                else:
                    x1 = int(cx + (raio_ext) * math.cos(ang_rad))
                    y1 = int(cy + (raio_ext) * math.sin(ang_rad))
                    x2 = int(cx + (raio_int + 15) * math.cos(ang_rad))
                    y2 = int(cy + (raio_int + 15) * math.sin(ang_rad))
                    cv2.line(frame, (x1, y1), (x2, y2), cor_tick, 1)
    
            prop_vd = vd / mv
            ang_vd = ang_inicio + (prop_vd * faixa_ang)
            cor_v  = (255, 255, 0) if prop_vd < 0.8 else (255, 0, 255)
            if vd_real < -0.5:
                cor_v = (0, 165, 255) # Laranja para Ré
            
            cv2.ellipse(frame, (cx, cy), (raio_ext - 3, raio_ext - 3), 0, ang_inicio, ang_vd, cor_v, 6)
            
            texto_vd = f"{int(vd_abs):02d}"
            (tw, th), _ = cv2.getTextSize(texto_vd, cv2.FONT_HERSHEY_DUPLEX, 2.5, 4)
            cv2.putText(frame, texto_vd, (cx - tw//2, cy + th//2 - 10), cv2.FONT_HERSHEY_DUPLEX, 2.5, (255, 255, 255), 4)
            
            # Unidade e Marcha
            marcha = "R" if vd_real < -0.5 else "D"
            cv2.putText(frame, marcha, (cx - 10, cy + 30), cv2.FONT_HERSHEY_DUPLEX, 0.8, cor_v, 2)
            cv2.putText(frame, "km/h", (cx - 20, cy + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            px_ag = int(cx + (raio_int - 20) * math.cos(math.radians(ang_vd)))
            py_ag = int(cy + (raio_int - 20) * math.sin(math.radians(ang_vd)))
            cv2.line(frame, (cx, cy), (px_ag, py_ag), cor_v, 3)
            cv2.circle(frame, (cx, cy), 6, (255, 255, 255), -1)

        elif self.layout == "cyber":
            cx, cy = W // 2, H // 2
            
            # Crosshair central estilo combate
            cv2.circle(frame, (cx, cy), 40, (0, 255, 0), 1)
            cv2.line(frame, (cx - 60, cy), (cx - 20, cy), (0, 255, 0), 2)
            cv2.line(frame, (cx + 20, cy), (cx + 60, cy), (0, 255, 0), 2)
            cv2.line(frame, (cx, cy - 60), (cx, cy - 20), (0, 255, 0), 2)
            cv2.line(frame, (cx, cy + 20), (cx, cy + 60), (0, 255, 0), 2)
            cv2.circle(frame, (cx, cy), 2, (0, 0, 255), -1)
            
            # Retangulos de tracking nas bordas do alvo
            cv2.rectangle(frame, (cx - 150, cy - 100), (cx - 120, cy - 70), (0, 255, 255), 2)
            cv2.rectangle(frame, (cx + 120, cy + 70), (cx + 150, cy + 100), (0, 255, 255), 2)
            
            # G-Meter no canto (onde ficava o velocimetro)
            g_cx, g_cy = 180, H - 150
            g_raio = 90
            
            over_g = frame.copy()
            cv2.circle(over_g, (g_cx, g_cy), g_raio + 10, (0, 0, 0), -1)
            cv2.addWeighted(over_g, 0.5, frame, 0.5, 0, frame)
            
            cv2.circle(frame, (g_cx, g_cy), g_raio, (255, 255, 255), 1)
            cv2.circle(frame, (g_cx, g_cy), g_raio // 2, (100, 100, 100), 1)
            cv2.line(frame, (g_cx - g_raio, g_cy), (g_cx + g_raio, g_cy), (100, 100, 100), 1)
            cv2.line(frame, (g_cx, g_cy - g_raio), (g_cx, g_cy + g_raio), (100, 100, 100), 1)
            
            # Calcula Gs visuais
            accel_long = self.aceleracao_ms2 / 9.8 
            accel_lat = telemetria_ext.get("aceleracao_x", 0.0) / 9.8 if self.modo == "sensor" else math.sin(time.time() * 2) * 0.2
            
            accel_long_lim = max(-1.5, min(1.5, accel_long))
            accel_lat_lim  = max(-1.5, min(1.5, accel_lat))
            
            px = int(g_cx + (accel_lat_lim / 1.5) * g_raio)
            py = int(g_cy - (accel_long_lim / 1.5) * g_raio) 
            
            cv2.circle(frame, (px, py), 8, (0, 255, 255), -1)
            cv2.putText(frame, "G-METER", (g_cx - 30, g_cy + g_raio + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            cv2.putText(frame, f"G: {abs(accel_long):.2f}", (g_cx - 20, g_cy - g_raio - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # ---------------------------------------------------------
        # PAINEL DE DADOS DE CORRIDA (Lateral Direita)
        # ---------------------------------------------------------
        cv2.putText(frame, "TELEMETRIA", (dx + 15, dy + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        cv2.putText(frame, f"MEDIA:  {self.velocidade_media_kmh:.1f} km/h",
                    (dx + 15, dy + 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(frame, f"MAXIMA: {self.velocidade_maxima:.1f} km/h",
                    (dx + 15, dy + 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 1)
        
        cor_a = (255, 255, 0) if self.aceleracao_ms2 >= 0 else (255, 0, 255)
        cv2.putText(frame, f"ACEL:   {self.aceleracao_ms2:+.2f} m/s2",
                    (dx + 15, dy + 135), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor_a, 2)
                    
        # Dados do Celular (Sensor Logger)
        if time.time() - telemetria_ext["ultima_att"] < 2.0:
            gps_kmh = telemetria_ext["gps_speed_ms"] * 3.6
            accel_y = telemetria_ext["aceleracao_y"]
            cv2.line(frame, (dx + 10, dy + 150), (dx + 260, dy + 150), (100, 100, 100), 1)
            cv2.putText(frame, "SENSOR CELULAR", (dx + 15, dy + 170), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.putText(frame, f"GPS:   {gps_kmh:.1f} km/h", (dx + 15, dy + 195), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            cv2.putText(frame, f"ACCEL: {accel_y:+.2f} m/s2", (dx + 15, dy + 215), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        cv2.putText(frame, "[C] Calib  [S] Modo  [L] Layout  [R] Reset  [Q] Sair",
                    (10, H - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)

        # Grafico
        gx, gy = W - 280, 280
        self._desenhar_grafico(frame, gx, gy, 270, 140)

        return frame

    # ──────────────────────────────────────────────────────────────────
    #  CÁLCULO PRINCIPAL
    # ──────────────────────────────────────────────────────────────────
    def calcular_velocidade(self, frame):
        frame_cinza_atual = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_debug       = frame.copy()

        tempo_atual  = time.time()
        delta_tempo  = tempo_atual - self.ultimo_tempo

        if self.modo == "demo":
            self.tempo_demo += delta_tempo
            ciclo = (self.tempo_demo % 12.0) / 12.0
            if ciclo < 0.4:
                accel_falsa = 5.0
            elif ciclo < 0.6:
                accel_falsa = 0.0
            elif ciclo < 0.9:
                accel_falsa = -6.0
            else:
                accel_falsa = 0.0
                
            self.velocidade_instantanea_kmh = max(0.0, min(120.0, self.velocidade_instantanea_kmh + accel_falsa * delta_tempo * 3.6))
            self.aceleracao_ms2 = accel_falsa * self.escala
            self.ultimo_tempo = tempo_atual
            
            # Atualiza stats base pra manter o grafico rodando
            self.historico_recente.append(self.velocidade_instantanea_kmh)
            if len(self.historico_recente) > 10: self.historico_recente.pop(0)
            
            self.soma_velocidades_curso += self.velocidade_instantanea_kmh
            self.qtd_medicoes_curso += 1
            self.velocidade_media_kmh = self.soma_velocidades_curso / self.qtd_medicoes_curso
            
            if self.velocidade_instantanea_kmh > self.velocidade_maxima:
                self.velocidade_maxima = self.velocidade_instantanea_kmh
                
            self.historico_grafico.append(self.velocidade_instantanea_kmh)
            if len(self.historico_grafico) > 300: self.historico_grafico.pop(0)
            
            return self.desenhar_painel(frame_debug)

        mediana_px, _ = self._extrair_flow(frame_cinza_atual, frame_debug)

        if self.modo not in ["sensor", "listras"] and (mediana_px is None or delta_tempo < 0.02):
            # Se nao ha fluxo ou frames rapidos demais, decair a velocidade suavemente
            if abs(self.velocidade_instantanea_kmh) > 0.5:
                self.velocidade_instantanea_kmh *= 0.85
                self.historico_recente = [self.velocidade_instantanea_kmh] * max(1, len(self.historico_recente))
            else:
                self.velocidade_instantanea_kmh = 0.0
                
            self.aceleracao_ms2 = 0.0
            self.ultimo_tempo = tempo_atual
            return self.desenhar_painel(frame_debug)

        # Acumula pixels durante calibração
        if self.calibrando:
            self.calib_pixels_acumulados += abs(mediana_px)
            self.calib_frames += 1
            cv2.putText(frame_debug,
                        f"CALIBRANDO... {self.calib_pixels_acumulados:.0f} px | [C] para finalizar",
                        (20, H_CAL := frame_debug.shape[0] // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # ── CÁLCULO DE VELOCIDADE ──────────────────────────────────────
        velocidade_fisica_kmh = 0.0
        mediana_px_abs = abs(mediana_px) if mediana_px is not None else 0.0
        sinal = -1 if (mediana_px is not None and mediana_px < 0) else 1
        
        if self.modo == "listras":
            hsv = cv2.cvtColor(frame_debug, cv2.COLOR_BGR2HSV)
            mask_white = cv2.inRange(hsv, np.array([0, 0, 150]), np.array([180, 50, 255]))
            mask_yellow = cv2.inRange(hsv, np.array([15, 100, 100]), np.array([40, 255, 255]))
            mask = cv2.bitwise_or(mask_white, mask_yellow)
            
            H_frame = frame_debug.shape[0]
            linha_deteccao = H_frame - 150
            mask[:linha_deteccao - 100, :] = 0 # Ignora coisas longe
            
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.line(frame_debug, (0, linha_deteccao), (frame_debug.shape[1], linha_deteccao), (0, 0, 255), 2)
            cv2.putText(frame_debug, "LINHA DE DETECCAO DE FAIXAS", (20, linha_deteccao - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            faixa_cruzando = False
            for cnt in contours:
                if cv2.contourArea(cnt) > 2000:
                    x, y, w, h = cv2.boundingRect(cnt)
                    if y < linha_deteccao < y + h:
                        faixa_cruzando = True
                        cv2.rectangle(frame_debug, (x, y), (x+w, y+h), (0, 255, 0), 4)
                        break
                        
            if faixa_cruzando and not self.faixa_passando:
                self.faixa_passando = True
                if self.ultimo_tempo_listra is not None:
                    dt_listra = tempo_atual - self.ultimo_tempo_listra
                    if dt_listra > 0.3:
                        vel_ms = self.distancia_listras_m / dt_listra
                        velocidade_fisica_kmh = vel_ms * 3.6
                self.ultimo_tempo_listra = tempo_atual
            elif not faixa_cruzando:
                self.faixa_passando = False
                
            if self.ultimo_tempo_listra is None:
                velocidade_fisica_kmh = 0.0
            else:
                dt_listra = tempo_atual - self.ultimo_tempo_listra
                if dt_listra > 2.0:
                    velocidade_fisica_kmh = (self.velocidade_instantanea_kmh / self.escala) * 0.95
                elif velocidade_fisica_kmh == 0.0:
                    velocidade_fisica_kmh = self.velocidade_instantanea_kmh / self.escala
                    
            velocidade_fisica_kmh = min(max(velocidade_fisica_kmh, 0.0), VEL_MAX_CARRINHO_KMH)

        elif self.modo == "sensor":
            gps_kmh = telemetria_ext["gps_speed_ms"] * 3.6
            accel_y = telemetria_ext["aceleracao_y"]
            
            if gps_kmh > 1.0:
                velocidade_fisica_kmh = gps_kmh
            else:
                if abs(accel_y) < 0.3:
                    velocidade_fisica_kmh = (self.velocidade_instantanea_kmh / self.escala) * 0.92
                else:
                    vel_ms = accel_y * delta_tempo
                    velocidade_fisica_kmh = (self.velocidade_instantanea_kmh / self.escala) + (vel_ms * 3.6)
            
            velocidade_fisica_kmh = min(max(velocidade_fisica_kmh, -VEL_MAX_CARRINHO_KMH), VEL_MAX_CARRINHO_KMH)

        elif self.modo == "real" and self.fator_px_mm is not None:
            # Modo REAL — conversão física direta
            if mediana_px_abs >= 0.3: # Tolerância menor para captar baixas velocidades
                desl_mm               = mediana_px_abs * self.fator_px_mm
                vel_ms                = (desl_mm / 1000.0) / delta_tempo
                velocidade_fisica_kmh = min(vel_ms * 3.6, VEL_MAX_CARRINHO_KMH) * sinal
        else:
            # Modo SIMULADO — normaliza pelo flow máximo observado
            if mediana_px_abs >= 0.3:
                flow_pxs = mediana_px_abs / delta_tempo
                if self.flow_maximo_observado_pxs is None or flow_pxs > self.flow_maximo_observado_pxs:
                    self.flow_maximo_observado_pxs = flow_pxs
                    self._salvar_calibracao()
                proporcao      = min(flow_pxs / self.flow_maximo_observado_pxs, 1.0)
                proporcao_s    = proporcao ** 0.75
                velocidade_fisica_kmh = proporcao_s * VEL_MAX_CARRINHO_KMH * sinal

        # A velocidade que exibimos no painel é a ESCALADA para dar imersão de corrida!
        velocidade_kmh = velocidade_fisica_kmh * self.escala

        # ── FILTRO ANTI-SPIKE ──────────────────────────────────────────
        vel_anterior      = self.velocidade_instantanea_kmh
        delta_v_aparente  = abs(velocidade_kmh - vel_anterior) / max(delta_tempo, 0.001)
        # Limite escalado: permitimos uma aceleração equivalente a um carro esportivo
        if delta_v_aparente > 150.0 and abs(velocidade_kmh) > 2.0:
            velocidade_kmh = vel_anterior * 0.75 + velocidade_kmh * 0.25

        # ── MÉDIA MÓVEL ────────────────────────────────────────────────
        self.historico_recente.append(velocidade_kmh)
        if len(self.historico_recente) > 10:
            self.historico_recente.pop(0)
        self.velocidade_instantanea_kmh = sum(self.historico_recente) / len(self.historico_recente)

        # ── ACELERAÇÃO (EM ESCALA) ─────────────────────────────────────
        delta_v_ms  = (self.velocidade_instantanea_kmh - vel_anterior) / 3.6
        accel_crua  = delta_v_ms / max(delta_tempo, 0.001)
        if abs(self.velocidade_instantanea_kmh) < 2.0:
            self.aceleracao_ms2 = 0.0
        else:
            self.aceleracao_ms2 = self.aceleracao_ms2 * 0.7 + accel_crua * 0.3

        # ── ESTATÍSTICAS ───────────────────────────────────────────────
        if self.velocidade_instantanea_kmh > self.velocidade_maxima:
            self.velocidade_maxima = self.velocidade_instantanea_kmh
        self.soma_velocidades_curso += self.velocidade_instantanea_kmh
        self.qtd_medicoes_curso     += 1
        self.velocidade_media_kmh    = self.soma_velocidades_curso / self.qtd_medicoes_curso
        self.historico_grafico.append(self.velocidade_instantanea_kmh)
        if len(self.historico_grafico) > 300:
            self.historico_grafico.pop(0)

        self.ultimo_tempo = tempo_atual
        return self.desenhar_painel(frame_debug)


# ==============================================================================
#  LOOP PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        if os.path.exists(".env"):
            with open(".env") as f:
                for linha in f:
                    if "=" in linha and not linha.startswith("#"):
                        k, v = linha.strip().split("=", 1)
                        os.environ[k] = v

    camera_ip    = os.getenv("CAMERA_IP")
    video_source = f"http://{camera_ip}/video" if camera_ip else 0
    print(f"[CAM] Fonte: {video_source}")

    cap = cv2.VideoCapture(video_source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)  # Reduz latência

    if not cap.isOpened():
        print("[ERRO] Não foi possível abrir a câmera!")
        exit()

    odometria = OdometriaVisual(escala=ESCALA_MAQUETE)

    cv2.namedWindow("Visao do Piloto - Neurodrive", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Visao do Piloto - Neurodrive", 1280, 720)

    print("\n[OK] Câmera conectada!")
    print("     [C] Calibrar 1m  |  [S] Modo  |  [R] Reset  |  [Q] Sair\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[AVISO] Frame perdido. Reconectando...")
            time.sleep(0.5)
            cap.open(video_source)
            continue

        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        if frame.shape[1] != 1280 or frame.shape[0] != 720:
            frame = cv2.resize(frame, (1280, 720))

        frame_out = odometria.calcular_velocidade(frame)
        cv2.imshow("Visao do Piloto - Neurodrive", frame_out)

        tecla = cv2.waitKey(1) & 0xFF
        if tecla in (ord('q'), ord('Q')):
            break
        odometria.processar_tecla(tecla)

    cap.release()
    cv2.destroyAllWindows()
    print("[FIM] Neurodrive encerrado.")
