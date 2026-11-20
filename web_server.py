import cv2
import threading
import time
import os
import json
import ipaddress
from urllib.parse import urlsplit, urlunsplit
from flask import Flask, Response, send_from_directory, stream_with_context, jsonify, request
from dotenv import load_dotenv

load_dotenv()

from neurodrive_pipeline import (
    AsyncIPCamera,
    ESCALA_MAQUETE,
    OdometriaVisual,
    criar_servidor_sensores,
    snapshot_telemetria,
)

CAMERA_IP = os.getenv("CAMERA_IP")
WEB_PORT  = int(os.getenv("WEB_PORT", "5000"))

app = Flask(__name__, static_folder="web")

frame_atual = None
frame_lock  = threading.Lock()
odometria   = OdometriaVisual(escala=ESCALA_MAQUETE)

nova_fonte = None
async_cam = None
fonte_lock = threading.Lock()
encerrar_event = threading.Event()
camera_thread = None
sensor_server = None
sensor_thread = None

REDES_CAMERA = tuple(
    ipaddress.ip_network(rede)
    for rede in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)


def normalizar_url_camera(valor):
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError("URL da câmera vazia")

    url = valor.strip()
    if "://" not in url:
        url = f"http://{url}"

    partes = urlsplit(url)
    if partes.scheme not in {"http", "https"}:
        raise ValueError("a câmera deve usar HTTP ou HTTPS")
    if partes.username or partes.password or partes.fragment:
        raise ValueError("credenciais e fragmentos não são aceitos na URL")

    try:
        host = ipaddress.ip_address(partes.hostname or "")
        porta = partes.port
    except ValueError as erro:
        raise ValueError("host ou porta inválidos") from erro

    if host.version != 4 or not any(host in rede for rede in REDES_CAMERA):
        raise ValueError("a câmera deve usar um endereço IPv4 privado da LAN")

    caminho = partes.path
    if caminho.endswith("/data"):
        caminho = f"{caminho[:-5]}/video"
    elif caminho in {"", "/"}:
        caminho = "/video"

    destino = str(host)
    if porta is not None:
        destino = f"{destino}:{porta}"
    return urlunsplit((partes.scheme, destino, caminho, partes.query, ""))

def camera_loop():
    global frame_atual, nova_fonte, async_cam

    try:
        video_source = normalizar_url_camera(CAMERA_IP) if CAMERA_IP else None
    except ValueError as erro:
        print(f"[CAM] Configuração ignorada: {erro}")
        video_source = None
    print(f"[CAM] Conectando em: {video_source}")
    
    if video_source is None:
        async_cam = None
    elif str(video_source).startswith("http"):
        async_cam = AsyncIPCamera(video_source)
    else:
        async_cam = cv2.VideoCapture(video_source)
        async_cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    while not encerrar_event.is_set():
        with fonte_lock:
            fonte_pendente = nova_fonte
            nova_fonte = None

        if fonte_pendente is not None:
            video_source = fonte_pendente
            if async_cam is not None:
                if isinstance(async_cam, AsyncIPCamera):
                    async_cam.stop()
                else:
                    async_cam.release()
                
            print(f"[CAM] Mudando fonte para: {video_source}")
            if str(video_source).startswith("http"):
                async_cam = AsyncIPCamera(video_source)
            else:
                async_cam = cv2.VideoCapture(video_source)
                async_cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            continue

        if async_cam is None:
            import numpy as np
            frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            cv2.putText(frame, "COLOQUE O IP DA CAMERA NO DASHBOARD", (250, 360), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 2)
            encerrar_event.wait(0.5)
        elif isinstance(async_cam, AsyncIPCamera):
            # Zero Delay: Pega apenas o frame recém decodificado na memória
            frame = async_cam.get_frame()
            if frame is None:
                continue
        else:
            ret, frame = async_cam.read()
            if not ret:
                encerrar_event.wait(0.5)
                with fonte_lock:
                    sem_nova_fonte = nova_fonte is None
                if sem_nova_fonte:
                    async_cam.open(video_source)
                continue
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            if frame.shape[1] != 1280 or frame.shape[0] != 720:
                frame = cv2.resize(frame, (1280, 720))

        # Optical flow ultraleve da V4.0
        processado = odometria.calcular_velocidade(frame)

        with frame_lock:
            frame_atual = processado


def iniciar_servicos():
    global camera_thread, sensor_server, sensor_thread
    if camera_thread is not None and camera_thread.is_alive():
        return

    encerrar_event.clear()
    sensor_server = criar_servidor_sensores()
    sensor_thread = threading.Thread(
        target=sensor_server.serve_forever,
        name="sensor-logger",
        daemon=True,
    )
    camera_thread = threading.Thread(
        target=camera_loop,
        name="camera-loop",
        daemon=True,
    )
    sensor_thread.start()
    camera_thread.start()


def encerrar_servicos():
    global camera_thread, sensor_server, sensor_thread, async_cam
    encerrar_event.set()
    if async_cam is not None:
        if isinstance(async_cam, AsyncIPCamera):
            async_cam.stop()
        else:
            async_cam.release()
        async_cam = None
    if sensor_server is not None:
        sensor_server.shutdown()
        sensor_server.server_close()
    for thread in (camera_thread, sensor_thread):
        if thread is not None:
            thread.join(timeout=1.0)
    camera_thread = None
    sensor_thread = None
    sensor_server = None

def gerar_mjpeg():
    # Loop agressivo para streaming MJPEG
    while not encerrar_event.is_set():
        with frame_lock:
            f = frame_atual
            
        if f is None:
            time.sleep(0.01)
            continue

        ok, jpeg = cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ok:
            continue

        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
        time.sleep(1 / 45) # Permite ate 45fps pro client consumir fluido


@app.route("/video")
def video_feed():
    return Response(
        stream_with_context(gerar_mjpeg()),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@app.route("/api/telemetria")
def telemetria_sse():
    def gerar():
        try:
            while True:
                telemetria = snapshot_telemetria()
                sensor_ativo = (time.time() - telemetria["ultima_att"]) < 2.0
                dados = {
                    "vel_inst":     round(odometria.velocidade_instantanea_kmh, 1),
                    "vel_media":    round(odometria.velocidade_media_kmh, 1),
                    "vel_max":      round(odometria.velocidade_maxima, 1),
                    "acel":         round(odometria.aceleracao_ms2, 2),
                    "modo":         odometria.modo,
                    "qualidade":    odometria.qualidade_rastreio,
                    "sensor_ativo": sensor_ativo,
                    "gps_kmh":      round(telemetria["gps_speed_ms"] * 3.6, 1) if sensor_ativo else None,
                    "accel_x":      round(telemetria["aceleracao_x"], 2) if sensor_ativo else None,
                    "accel_y":      round(telemetria["aceleracao_y"], 2) if sensor_ativo else None,
                    "historico":    list(odometria.historico_grafico[-60:]),
                }
                yield f"data: {json.dumps(dados)}\n\n"
                time.sleep(0.1) # Resposta mais rápida da telemetria (10Hz)
        except GeneratorExit:
            pass

    return Response(
        stream_with_context(gerar()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/galeria")
def listar_galeria():
    pasta = os.path.join("web", "assets", "gallery")
    if not os.path.exists(pasta):
        return jsonify([])
    exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    arquivos = [f for f in os.listdir(pasta) if os.path.splitext(f)[1].lower() in exts]
    return jsonify(sorted(arquivos))


@app.route("/api/config_camera", methods=["POST"])
def config_camera():
    global nova_fonte
    dados = request.get_json(silent=True)
    if dados and "url" in dados:
        try:
            url = normalizar_url_camera(dados["url"])
        except ValueError as erro:
            return jsonify({"error": str(erro)}), 400
        with fonte_lock:
            nova_fonte = url
        return jsonify({"status": "ok", "url": url})
    return jsonify({"error": "invalid"}), 400


@app.route("/api/tecla", methods=["POST"])
def receber_tecla():
    dados = request.get_json()
    if dados and "tecla" in dados:
        tecla = dados["tecla"].lower()
        if len(tecla) == 1:
            odometria.processar_tecla(ord(tecla))
            return jsonify({"status": "ok"})
    return jsonify({"error": "invalid"}), 400


@app.route("/")
def index():
    return send_from_directory("web", "index.html")


@app.route("/<path:filename>")
def arquivos_estaticos(filename):
    return send_from_directory("web", filename)


if __name__ == "__main__":
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()
        
    sensor_port = os.getenv("SENSOR_SERVER_PORT", "8000")
    print(f"\n{'='*50}")
    print(f"  NEURODRIVE WEB DASHBOARD - ZERO DELAY")
    print(f"{'='*50}")
    print(f"  Local  -> http://localhost:{WEB_PORT}")
    print(f"  Rede   -> http://{local_ip}:{WEB_PORT}")
    print(f"\n  Sensor Logger -> http://{local_ip}:{sensor_port}/data")
    print(f"{'='*50}\n")
    
    try:
        iniciar_servicos()
        app.run(host="0.0.0.0", port=WEB_PORT, threaded=True)
    finally:
        encerrar_servicos()
