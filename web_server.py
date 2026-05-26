import cv2
import threading
import time
import os
import json
from flask import Flask, Response, send_from_directory, stream_with_context, jsonify
from dotenv import load_dotenv

load_dotenv()

from neurodrive_pipeline import OdometriaVisual, telemetria_ext, ESCALA_MAQUETE

CAMERA_IP = os.getenv("CAMERA_IP")
WEB_PORT  = int(os.getenv("WEB_PORT", "5000"))

app = Flask(__name__, static_folder="web")

frame_atual = None
frame_lock  = threading.Lock()
odometria   = OdometriaVisual(escala=ESCALA_MAQUETE)


def camera_loop():
    global frame_atual
    video_source = f"http://{CAMERA_IP}/video" if CAMERA_IP else 0
    print(f"[CAM] Conectando em: {video_source}")
    cap = cv2.VideoCapture(video_source)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.5)
            cap.open(video_source)
            continue

        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        if frame.shape[1] != 1280 or frame.shape[0] != 720:
            frame = cv2.resize(frame, (1280, 720))

        processado = odometria.calcular_velocidade(frame)

        with frame_lock:
            frame_atual = processado


threading.Thread(target=camera_loop, daemon=True).start()


def gerar_mjpeg():
    while True:
        with frame_lock:
            f = frame_atual

        if f is None:
            time.sleep(0.05)
            continue

        ok, jpeg = cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            continue

        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
        time.sleep(1 / 30)


@app.route("/video")
def video_feed():
    return Response(
        stream_with_context(gerar_mjpeg()),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/api/telemetria")
def telemetria_sse():
    def gerar():
        try:
            while True:
                sensor_ativo = (time.time() - telemetria_ext["ultima_att"]) < 2.0
                dados = {
                    "vel_inst":     round(odometria.velocidade_instantanea_kmh, 1),
                    "vel_media":    round(odometria.velocidade_media_kmh, 1),
                    "vel_max":      round(odometria.velocidade_maxima, 1),
                    "acel":         round(odometria.aceleracao_ms2, 2),
                    "modo":         odometria.modo,
                    "qualidade":    odometria.qualidade_rastreio,
                    "sensor_ativo": sensor_ativo,
                    "gps_kmh":      round(telemetria_ext["gps_speed_ms"] * 3.6, 1) if sensor_ativo else None,
                    "accel_x":      round(telemetria_ext["aceleracao_x"], 2) if sensor_ativo else None,
                    "accel_y":      round(telemetria_ext["aceleracao_y"], 2) if sensor_ativo else None,
                    "historico":    list(odometria.historico_grafico[-60:]),
                }
                yield f"data: {json.dumps(dados)}\n\n"
                time.sleep(0.2)
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


@app.route("/")
def index():
    return send_from_directory("web", "index.html")


@app.route("/<path:filename>")
def arquivos_estaticos(filename):
    return send_from_directory("web", filename)


if __name__ == "__main__":
    sensor_port = os.getenv("SENSOR_SERVER_PORT", "8000")
    print(f"\n{'='*50}")
    print(f"  NEURODRIVE WEB DASHBOARD")
    print(f"{'='*50}")
    print(f"  Local  → http://localhost:{WEB_PORT}")
    print(f"  Rede   → http://<seu-ip>:{WEB_PORT}")
    print(f"\n  Acesso global: ngrok http {WEB_PORT}")
    print(f"  Sensor Logger → porta {sensor_port}")
    print(f"{'='*50}\n")
    app.run(host="0.0.0.0", port=WEB_PORT, threaded=True)
