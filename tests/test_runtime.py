import http.client
import json
import threading

import numpy as np
import pytest

pytest.importorskip("cv2")

import neurodrive_pipeline
import web_server


def _post_sensor(server, payload, path="/data"):
    conexao = http.client.HTTPConnection(*server.server_address, timeout=2)
    corpo = json.dumps(payload)
    conexao.request(
        "POST",
        path,
        body=corpo,
        headers={"Content-Type": "application/json"},
    )
    resposta = conexao.getresponse()
    resposta.read()
    conexao.close()
    return resposta.status


@pytest.fixture
def sensor_server():
    server = neurodrive_pipeline.criar_servidor_sensores("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_importar_web_server_nao_inicia_servicos():
    assert web_server.camera_thread is None
    assert web_server.sensor_thread is None
    assert web_server.sensor_server is None


@pytest.mark.parametrize(
    "entrada,esperada",
    [
        ("192.168.1.20:8080", "http://192.168.1.20:8080/video"),
        ("http://10.0.0.2/data", "http://10.0.0.2/video"),
        ("https://172.16.4.3/stream", "https://172.16.4.3/stream"),
    ],
)
def test_normalizar_url_camera_da_lan(entrada, esperada):
    assert web_server.normalizar_url_camera(entrada) == esperada


@pytest.mark.parametrize(
    "entrada",
    [
        "ftp://192.168.1.20/video",
        "http://127.0.0.1:5000/",
        "http://169.254.169.254/",
        "http://8.8.8.8/video",
        "http://camera.local/video",
        "http://user:senha@192.168.1.20/video",
    ],
)
def test_rejeitar_url_camera_fora_do_contrato_lan(entrada):
    with pytest.raises(ValueError):
        web_server.normalizar_url_camera(entrada)


def test_endpoint_camera_devolve_url_normalizada():
    with web_server.app.test_client() as client:
        resposta = client.post(
            "/api/config_camera", json={"url": "192.168.1.20:8080"}
        )

    assert resposta.status_code == 200
    assert resposta.get_json()["url"] == "http://192.168.1.20:8080/video"


def test_sensor_logger_atualiza_snapshot(sensor_server):
    status = _post_sensor(
        sensor_server,
        {
            "payload": [
                {
                    "name": "accelerometer",
                    "values": {"x": 1.2, "y": -0.5, "z": 9.8},
                },
                {"name": "location", "values": {"speed": 2.5}},
            ]
        },
    )

    snapshot = neurodrive_pipeline.snapshot_telemetria()
    assert status == 200
    assert snapshot["aceleracao_x"] == pytest.approx(1.2)
    assert snapshot["gps_speed_ms"] == pytest.approx(2.5)


def test_sensor_logger_rejeita_valor_nao_numerico(sensor_server):
    status = _post_sensor(
        sensor_server,
        {"payload": [{"name": "location", "values": {"speed": "rápido"}}]},
    )

    assert status == 400


def test_sensor_logger_rejeita_rota_incorreta(sensor_server):
    assert _post_sensor(sensor_server, {"payload": []}, path="/outra") == 404


@pytest.mark.parametrize("layout", ["velocimetro", "cyber"])
def test_painel_preserva_dimensoes_nos_dois_layouts(layout):
    odometria = neurodrive_pipeline.OdometriaVisual()
    odometria.layout = layout
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    resultado = odometria.desenhar_painel(frame)

    assert resultado.shape == frame.shape


def test_primeiro_frame_sem_pontos_nao_quebra_pipeline():
    odometria = neurodrive_pipeline.OdometriaVisual()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    resultado = odometria.calcular_velocidade(frame)

    assert resultado.shape == frame.shape
    assert odometria.velocidade_instantanea_kmh == 0


def test_modo_demo_atualiza_sem_camera_real():
    odometria = neurodrive_pipeline.OdometriaVisual()
    odometria.modo = "demo"
    odometria.ultimo_tempo -= 0.1
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    odometria.calcular_velocidade(frame)

    assert odometria.velocidade_instantanea_kmh > 0
