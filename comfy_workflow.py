# -*- coding: utf-8 -*-
"""
ComfyUI 워크플로 동적 조립 및 실행 모듈.
로컬 ComfyUI 서버와 HTTP/WebSocket으로 통신하며, JSON 템플릿을 합쳐 워크플로를 생성·실행합니다.
"""

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests
import websocket

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------
DEFAULT_SERVER = "http://127.0.0.1:8188"
WS_SERVER = "ws://127.0.0.1:8188/ws"
NODE_ID_OFFSET = 1000
TEMPLATES_DIR = Path(__file__).resolve().parent / "node_templates"
OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs"
REQUEST_TIMEOUT = 30
WS_RECV_TIMEOUT = 3600


# ---------------------------------------------------------------------------
# 템플릿 로드 및 오프셋
# ---------------------------------------------------------------------------
def load_template(name: str) -> dict:
    """
    node_templates/ 폴더에서 JSON 템플릿을 로드합니다.
    :param name: 파일명(확장자 제외), 예: "text2img", "upscale"
    :return: 템플릿 워크플로 딕셔너리
    """
    path = TEMPLATES_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"템플릿을 찾을 수 없습니다: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _apply_offset_to_value(val: Any, offset: int) -> Any:
    """값 내부의 노드 참조 [node_id, slot]에 offset을 적용합니다."""
    if isinstance(val, dict):
        return {k: _apply_offset_to_value(v, offset) for k, v in val.items()}
    if isinstance(val, list):
        if (
            len(val) == 2
            and isinstance(val[0], str)
            and val[0].isdigit()
            and isinstance(val[1], (int, float))
        ):
            return [str(int(val[0]) + offset), val[1]]
        return [_apply_offset_to_value(x, offset) for x in val]
    return val


def apply_offset(template: dict, offset: int) -> dict:
    """
    템플릿의 모든 노드 ID와 내부 참조에 offset을 더합니다.
    :param template: 원본 템플릿
    :param offset: 더할 값 (예: 1000)
    :return: 오프셋이 적용된 새 워크플로
    """
    result = {}
    for node_id, node_data in template.items():
        if not isinstance(node_data, dict):
            result[str(int(node_id) + offset)] = node_data
            continue
        new_id = str(int(node_id) + offset)
        result[new_id] = _apply_offset_to_value(node_data, offset)
    return result


def merge_templates(template_names: List[str]) -> dict:
    """
    여러 템플릿을 1000 단위 오프셋으로 합쳐 하나의 워크플로로 만듭니다.
    :param template_names: 템플릿 이름 리스트 (예: ["text2img", "upscale"])
    :return: 병합된 워크플로
    """
    workflow = {}
    for i, name in enumerate(template_names):
        template = load_template(name)
        offset = i * NODE_ID_OFFSET
        workflow.update(apply_offset(template, offset))
    return workflow


# ---------------------------------------------------------------------------
# 연결 및 노드 조작
# ---------------------------------------------------------------------------
def connect(
    workflow: dict,
    output_node_id: Union[str, int],
    input_node_id: Union[str, int],
    input_key: str,
    output_slot: int = 0,
) -> None:
    """
    앞 모드의 출력을 다음 모드의 입력에 연결합니다.
    workflow를 in-place로 수정합니다.
    :param workflow: 대상 워크플로
    :param output_node_id: 출력을 내보내는 노드 ID
    :param input_node_id: 입력을 받을 노드 ID
    :param input_key: 입력 노드의 입력 슬롯 키 (예: "image", "samples")
    :param output_slot: 출력 노드의 슬롯 인덱스 (기본 0)
    """
    out_id = str(output_node_id)
    in_id = str(input_node_id)
    if in_id not in workflow:
        raise KeyError(f"워크플로에 노드가 없습니다: {in_id}")
    if "inputs" not in workflow[in_id]:
        workflow[in_id]["inputs"] = {}
    workflow[in_id]["inputs"][input_key] = [out_id, output_slot]


def find_nodes_by_class(workflow: dict, class_type: str) -> List[str]:
    """
    class_type과 일치하는 노드 ID 목록을 반환합니다.
    :param workflow: 워크플로
    :param class_type: 노드 클래스명 (예: "SaveImage", "KSampler")
    :return: 노드 ID 문자열 리스트
    """
    return [
        nid
        for nid, data in workflow.items()
        if isinstance(data, dict) and data.get("class_type") == class_type
    ]


def set_node_input(
    workflow: dict,
    node_id: Union[str, int],
    key: str,
    value: Any,
) -> None:
    """
    특정 노드의 입력 값을 설정합니다.
    :param workflow: 워크플로
    :param node_id: 노드 ID
    :param key: 입력 키
    :param value: 설정할 값 (숫자, 문자열, [node_id, slot] 등)
    """
    nid = str(node_id)
    if nid not in workflow:
        raise KeyError(f"워크플로에 노드가 없습니다: {nid}")
    if "inputs" not in workflow[nid]:
        workflow[nid]["inputs"] = {}
    workflow[nid]["inputs"][key] = value


def apply_placeholders(workflow: dict, replacements: Dict[str, Any]) -> None:
    """
    워크플로 전체에서 __NAME__ 형태의 플레이스홀더를 치환합니다.
    workflow를 in-place로 수정합니다.
    :param workflow: 대상 워크플로
    :param replacements: {"__PROMPT__": "a cat", "__SEED__": 42} 형태
    """
    for node_id, node_data in workflow.items():
        if not isinstance(node_data, dict) or "inputs" not in node_data:
            continue
        for key, val in list(node_data["inputs"].items()):
            node_data["inputs"][key] = _replace_placeholders_recursive(val, replacements)


def _replace_placeholders_recursive(val: Any, replacements: Dict[str, Any]) -> Any:
    if isinstance(val, dict):
        return {k: _replace_placeholders_recursive(v, replacements) for k, v in val.items()}
    if isinstance(val, list):
        return [_replace_placeholders_recursive(x, replacements) for x in val]
    if isinstance(val, str) and val in replacements:
        return replacements[val]
    return val


# ---------------------------------------------------------------------------
# 워크플로 빌드
# ---------------------------------------------------------------------------
def build_workflow(config: dict) -> dict:
    """
    설정값에 따라 최종 워크플로 JSON을 생성합니다.
    :param config: {
        "modes": ["text2img", "upscale"],  # 사용할 템플릿 순서
        "params": {                         # 모드별 파라미터 (오프셋된 노드 ID 또는 class_type 기준)
            "text2img": {"__PROMPT__": "...", "__SEED__": 123},
            "upscale": {}
        },
        "connections": [                    # 모드 간 연결 (오프셋 적용된 노드 ID)
            {"from_node": "8", "from_slot": 0, "to_node": "1003", "to_input": "image"}
        ],
        "placeholders": {"__PROMPT__": "a cat", "__SEED__": 42}  # 전역 플레이스홀더 (선택)
    }
    :return: ComfyUI /prompt 에 넣을 수 있는 워크플로 딕셔너리
    """
    modes = config.get("modes", [])
    if not modes:
        raise ValueError("config['modes']가 비어 있을 수 없습니다.")

    workflow = merge_templates(modes)

    # 연결 적용
    for conn in config.get("connections", []):
        connect(
            workflow,
            conn["from_node"],
            conn["to_node"],
            conn["to_input"],
            conn.get("from_slot", 0),
        )

    # 전역 플레이스홀더 + 모드별 params에서 __X__ 형태만 수집
    placeholders = dict(config.get("placeholders", {}))
    for mode_params in config.get("params", {}).values():
        for key, value in mode_params.items():
            if isinstance(key, str) and key.startswith("__") and key.endswith("__"):
                placeholders[key] = value

    apply_placeholders(workflow, placeholders)
    return workflow


# ---------------------------------------------------------------------------
# ComfyUI 서버 통신 및 이미지 생성
# ---------------------------------------------------------------------------
def queue_prompt(
    workflow: dict,
    server: str = DEFAULT_SERVER,
    client_id: Optional[str] = None,
    prompt_id: Optional[str] = None,
    timeout: int = REQUEST_TIMEOUT,
) -> str:
    """
    워크플로를 /prompt에 전송하고 prompt_id를 반환합니다.
    :param workflow: build_workflow()로 만든 워크플로
    :param server: 기본 http://127.0.0.1:8188
    :param client_id: WebSocket 클라이언트 ID (선택)
    :param prompt_id: 지정 시 해당 ID 사용, 없으면 UUID 생성
    :param timeout: 요청 타임아웃(초)
    :return: prompt_id
    """
    prompt_id = prompt_id or str(uuid.uuid4())
    payload = {
        "prompt": workflow,
        "client_id": client_id or str(uuid.uuid4()),
        "prompt_id": prompt_id,
    }
    url = f"{server.rstrip('/')}/prompt"
    resp = requests.post(url, json=payload, timeout=timeout)
    if not resp.ok:
        raise RuntimeError(f"ComfyUI /prompt 오류 ({resp.status_code}): {resp.text[:800]}")
    data = resp.json()
    if "prompt_id" in data:
        return data["prompt_id"]
    if "error" in data:
        raise RuntimeError(f"ComfyUI 오류: {data['error']}")
    return prompt_id


def upload_image(
    server: str,
    image_path: Union[str, Path],
    subfolder: str = "",
    folder_type: str = "input",
    overwrite: bool = False,
    timeout: int = REQUEST_TIMEOUT,
) -> dict:
    """
    이미지를 ComfyUI 서버에 업로드합니다. img2img 등에서 기준 이미지로 사용.
    :return: {"name": filename, "subfolder": subfolder, "type": folder_type}
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"이미지가 없습니다: {path}")
    url = f"{server.rstrip('/')}/upload/image"
    with open(path, "rb") as f:
        files = {"image": (path.name, f, "image/png")}
        data = {"subfolder": subfolder, "type": folder_type}
        if overwrite:
            data["overwrite"] = "true"
        resp = requests.post(url, files=files, data=data, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def get_history(server: str, prompt_id: str, timeout: int = REQUEST_TIMEOUT) -> dict:
    """/history/{prompt_id} 결과를 반환합니다."""
    url = f"{server.rstrip('/')}/history/{prompt_id}"
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def get_available_checkpoints(
    server: str = DEFAULT_SERVER,
    timeout: int = REQUEST_TIMEOUT,
) -> List[str]:
    """ComfyUI /models/checkpoints 에서 사용 가능한 체크포인트 파일명 목록을 반환합니다."""
    url = f"{server.rstrip('/')}/models/checkpoints"
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def get_image(
    server: str,
    filename: str,
    subfolder: str = "",
    folder_type: str = "output",
    timeout: int = REQUEST_TIMEOUT,
) -> bytes:
    """/view 로 이미지 바이트를 가져옵니다."""
    base = server.rstrip("/")
    params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    resp = requests.get(f"{base}/view", params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def wait_execution_done(
    ws: websocket.WebSocket,
    prompt_id: str,
    recv_timeout: float = WS_RECV_TIMEOUT,
) -> None:
    """
    WebSocket으로 실행 완료(node is None)까지 대기합니다.
    """
    while True:
        try:
            out = ws.recv()
        except websocket.WebSocketTimeoutException:
            raise TimeoutError(f"실행 대기 시간 초과 (prompt_id={prompt_id})")
        if isinstance(out, bytes):
            continue
        try:
            msg = json.loads(out)
        except json.JSONDecodeError:
            continue
        if msg.get("type") != "executing":
            continue
        data = msg.get("data", {})
        if data.get("node") is None and data.get("prompt_id") == prompt_id:
            break


def generate_image(
    workflow: dict,
    server: str = DEFAULT_SERVER,
    save_dir: Optional[Union[str, Path]] = None,
    client_id: Optional[str] = None,
    request_timeout: int = REQUEST_TIMEOUT,
    ws_timeout: float = WS_RECV_TIMEOUT,
) -> List[Path]:
    """
    워크플로를 /prompt로 전송하고 WebSocket으로 진행 상황을 추적한 뒤,
    결과 이미지를 save_dir(기본 ./outputs/)에 저장합니다.
    :param workflow: build_workflow()로 만든 워크플로
    :param server: ComfyUI 서버 URL
    :param save_dir: 저장 디렉터리 (None이면 OUTPUTS_DIR)
    :param client_id: WebSocket client_id (None이면 UUID)
    :param request_timeout: HTTP 타임아웃(초)
    :param ws_timeout: WebSocket recv 타임아웃(초)
    :return: 저장된 이미지 파일 경로 리스트
    """
    save_dir = Path(save_dir) if save_dir else OUTPUTS_DIR
    save_dir.mkdir(parents=True, exist_ok=True)

    base = server.rstrip("/")
    host = base.replace("http://", "").replace("https://", "").split("/")[0]
    ws_url = f"wss://{host}/ws" if base.startswith("https") else f"ws://{host}/ws"

    cid = client_id or str(uuid.uuid4())
    prompt_id = queue_prompt(workflow, server=server, client_id=cid, timeout=request_timeout)

    ws = websocket.WebSocket()
    try:
        ws.settimeout(ws_timeout)
        ws.connect(f"{ws_url}?clientId={cid}")
        wait_execution_done(ws, prompt_id, recv_timeout=ws_timeout)
    finally:
        ws.close()

    history = get_history(server, prompt_id, timeout=request_timeout)
    if prompt_id not in history:
        raise RuntimeError(f"history에 prompt_id가 없습니다: {prompt_id}")

    # ComfyUI 버전에 따라 "outputs" 또는 "output" 등일 수 있음
    outputs = history[prompt_id].get("outputs") or history[prompt_id].get("output") or {}
    saved_paths = []
    for node_id, node_out in outputs.items():
        if "images" not in node_out:
            continue
        for img in node_out["images"]:
            subfolder = img.get("subfolder", "")
            folder_type = img.get("type", "output")
            filename = img["filename"]
            data = get_image(server, filename, subfolder, folder_type, timeout=request_timeout)
            out_path = save_dir / filename
            out_path.write_bytes(data)
            saved_paths.append(out_path)

    if not saved_paths:
        status = history[prompt_id].get("status", [])
        err_parts = []
        for s in status:
            if isinstance(s, dict):
                err_parts.append(s.get("status_str", "") or str(s.get("messages", s)))
            else:
                err_parts.append(str(s))
        out_keys = list(outputs.keys())
        err_msg = "; ".join(err_parts) if err_parts else "outputs 비어 있음"
        raise RuntimeError(
            f"ComfyUI에서 이미지가 반환되지 않았습니다. status={err_msg} outputs노드={out_keys}. "
            "체크포인트가 ComfyUI의 models/checkpoints 에 있는지 확인하세요."
        )

    return saved_paths


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------
def remove_node(workflow: dict, node_id: Union[str, int]) -> None:
    """
    워크플로에서 노드를 제거합니다.
    다른 노드가 이 노드를 참조하면 실행 시 오류가 날 수 있으므로,
    연결로 대체할 때만 사용하세요.
    """
    workflow.pop(str(node_id), None)


def update_workflow_by_node_id(
    workflow: dict,
    node_id: Union[str, int],
    updates: Dict[str, Any],
) -> None:
    """
    특정 노드 ID의 inputs를 일괄 수정합니다.
    :param workflow: 워크플로
    :param node_id: 노드 ID
    :param updates: {"seed": 123, "steps": 30} 형태
    """
    nid = str(node_id)
    if nid not in workflow:
        raise KeyError(f"노드가 없습니다: {nid}")
    if "inputs" not in workflow[nid]:
        workflow[nid]["inputs"] = {}
    workflow[nid]["inputs"].update(updates)
