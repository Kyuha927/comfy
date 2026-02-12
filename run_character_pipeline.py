# -*- coding: utf-8 -*-
"""
게임용 픽셀 캐릭터 일관 생성 파이프라인.
- txt2img: 베이스 캐릭터 1회 생성 (denoise 1.0)
- img2img: 기준 이미지로 Identity Lock, 파츠만 변경 (denoise 0.35~0.45)
"""

import argparse
import json
import re
from pathlib import Path
from typing import List, Optional

import comfy_workflow as cw

CONFIGS_DIR = Path(__file__).resolve().parent / "configs"
OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs"
DEFAULT_SERVER = "http://127.0.0.1:8188"

# 일러스트 방지: 사용 금지 키워드
FORBIDDEN_PROMPT = ("masterpiece", "best quality", "ultra detailed", "highly detailed")
# 목적형 키워드만 허용 (추가 가능)
ALLOWED_BASE = (
    "pixel game character sprite", "flat colors", "simple shading",
    "clear outline", "game asset", "front view", "standing pose",
)
IMG2IMG_DENOISE = 0.4
IMG2IMG_CFG = 6.75  # 6.5 ~ 7 권장


def sanitize_filename(s: str) -> str:
    """파일명에 쓸 수 있도록 안전한 문자열로 만듦."""
    s = s.strip().lower()
    s = re.sub(r"[^\w\-.]", "_", s)
    return re.sub(r"_+", "_", s).strip("_") or "unknown"


def filter_prompt(raw: str) -> str:
    """금지 키워드 제거, 목적형만 유지."""
    lower = raw.lower()
    for w in FORBIDDEN_PROMPT:
        lower = re.sub(re.escape(w), "", lower, flags=re.I)
    lower = re.sub(r",\s*,", ",", lower).strip(" ,")
    return lower or "pixel game character sprite, flat colors, standing pose, front view"


def build_prompt_from_config(config: dict, for_img2img: bool = False) -> str:
    """base_character.base_prompt + parts 조합. img2img 시 금지 키워드 제거."""
    base = config.get("base_character", {})
    parts = config.get("parts", {})

    base_prompt = base.get("base_prompt", "pixel game character sprite, flat colors, standing pose, front view")
    if for_img2img:
        base_prompt = filter_prompt(base_prompt)
    parts_list = []
    if parts.get("hair"):
        parts_list.append(f"hair: {parts['hair']}")
    if parts.get("top"):
        parts_list.append(f"top: {parts['top']}")
    if parts.get("bottom"):
        parts_list.append(f"bottom: {parts['bottom']}")
    if parts.get("shoes"):
        parts_list.append(f"shoes: {parts['shoes']}")
    if parts.get("item") and str(parts.get("item", "")).lower() not in ("empty", "", "none"):
        parts_list.append(f"holding: {parts['item']}")
    if parts.get("expression"):
        parts_list.append(f"expression: {parts['expression']}")

    if parts_list:
        out = f"{base_prompt}, {', '.join(parts_list)}"
    else:
        out = base_prompt
    return filter_prompt(out) if for_img2img else out


def build_filename_prefix(config: dict) -> str:
    """메타데이터 포함 파일명 접두사: character_base / hair / top / bottom / item / expression."""
    base = config.get("base_character", {})
    parts = config.get("parts", {})
    name = sanitize_filename(base.get("name", "character"))
    hair = sanitize_filename(str(parts.get("hair", "hair")))
    top = sanitize_filename(str(parts.get("top", "top")))
    bottom = sanitize_filename(str(parts.get("bottom", "bottom")))
    shoes = sanitize_filename(str(parts.get("shoes", "shoes")))
    item = sanitize_filename(str(parts.get("item", "empty")))
    expr = sanitize_filename(str(parts.get("expression", "neutral")))
    return f"{name}_{hair}_{top}_{bottom}_{shoes}_{item}_{expr}"


def load_config(path: Path) -> dict:
    """JSON 설정 파일 로드."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_pipeline(
    config_path: Path,
    server: str = DEFAULT_SERVER,
    save_dir: Optional[Path] = None,
    seed_override: Optional[int] = None,
    denoise_override: Optional[float] = None,
    ckpt_override: Optional[str] = None,
) -> List[Path]:
    """
    설정 파일 기준으로 캐릭터 이미지 1장 생성.
    - base_image 있음 → img2img (Identity Lock, denoise 0.4 전후)
    - base_image 없음 → txt2img (베이스 1회 생성, denoise 1.0)
    """
    config = load_config(config_path)
    base = config.get("base_character", {})
    seed = seed_override if seed_override is not None else base.get("seed", 42)
    ckpt_name = ckpt_override or base.get("ckpt_name", "v1-5-pruned-emaonly.safetensors")
    negative = config.get("negative_prompt", "blur, soft gradient, anti-aliasing, realistic, photograph")
    out_dir = save_dir or OUTPUTS_DIR
    base_image_path = config.get("base_image")

    if base_image_path:
        # img2img: 기준 이미지 업로드 후 Identity Lock
        base_image_path = Path(base_image_path)
        if not base_image_path.is_absolute():
            base_image_path = (config_path.parent / base_image_path).resolve()
        if not base_image_path.exists():
            raise FileNotFoundError(f"base_image을 찾을 수 없습니다: {base_image_path}")
        upload_result = cw.upload_image(server, base_image_path, folder_type="input")
        image_input = [upload_result["name"], upload_result.get("subfolder", "")]
        denoise = denoise_override if denoise_override is not None else IMG2IMG_DENOISE
        cfg = base.get("cfg_img2img", IMG2IMG_CFG)
        prompt = build_prompt_from_config(config, for_img2img=True)
        filename_prefix = build_filename_prefix(config)
        workflow_config = {
            "modes": ["img2img_character"],
            "placeholders": {
                "__PROMPT__": prompt,
                "__NEGATIVE__": negative,
                "__SEED__": seed,
                "__CKPT_NAME__": ckpt_name,
                "__FILENAME_PREFIX__": filename_prefix,
                "__DENOISE__": denoise,
                "__CFG__": cfg,
                "__IMAGE_INPUT__": image_input,
            },
        }
    else:
        # txt2img: 베이스 1회 생성
        prompt = build_prompt_from_config(config, for_img2img=False)
        filename_prefix = build_filename_prefix(config)
        steps = base.get("steps", 30)
        cfg = base.get("cfg", 8.5)
        sampler = base.get("sampler_name", "dpmpp_2m")
        scheduler = base.get("scheduler", "karras")
        width = base.get("width", 512)
        height = base.get("height", 512)
        workflow_config = {
            "modes": ["pixel_character"],
            "placeholders": {
                "__PROMPT__": prompt,
                "__NEGATIVE__": negative,
                "__SEED__": seed,
                "__CKPT_NAME__": ckpt_name,
                "__FILENAME_PREFIX__": filename_prefix,
                "__STEPS__": steps,
                "__CFG__": cfg,
                "__SAMPLER__": sampler,
                "__SCHEDULER__": scheduler,
                "__WIDTH__": width,
                "__HEIGHT__": height,
            },
        }

    workflow = cw.build_workflow(workflow_config)
    paths = cw.generate_image(workflow, server=server, save_dir=out_dir)
    
    # Save metadata
    meta = {
        "ckpt_name": ckpt_name,
        "seed": seed,
        "prompt": prompt,
        "negative_prompt": negative,
        "steps": config.get("base_character", {}).get("steps"),
        "cfg": config.get("base_character", {}).get("cfg"),
        "sampler": config.get("base_character", {}).get("sampler_name"),
        "scheduler": config.get("base_character", {}).get("scheduler"),
    }
    if base_image_path:
        meta["base_image"] = str(base_image_path)
        meta["denoise"] = denoise
        meta["cfg_img2img"] = cfg
    
    for p in paths:
        meta_path = p.with_suffix(".metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    return paths


def main():
    parser = argparse.ArgumentParser(description="게임용 픽셀 캐릭터 파이프라인 (ComfyUI API)")
    parser.add_argument(
        "config",
        nargs="?",
        default=CONFIGS_DIR / "example_character.json",
        type=Path,
        help="캐릭터 설정 JSON 경로 (기본: configs/example_character.json)",
    )
    parser.add_argument("--server", default=DEFAULT_SERVER, help="ComfyUI 서버 URL")
    parser.add_argument("--out", type=Path, default=None, help="저장 폴더 (기본: outputs/)")
    parser.add_argument("--seed", type=int, default=None, help="시드 고정 (설정 파일보다 우선)")
    parser.add_argument("--denoise", type=float, default=None, help="img2img denoise (0.35~0.45, 기본 0.4)")
    parser.add_argument("--ckpt", type=str, default=None, help="체크포인트 파일명 (예: anything-v5.0-pruned.safetensors)")
    args = parser.parse_args()

    if not args.config.exists():
        print(f"설정 파일이 없습니다: {args.config}")
        print("configs/example_character.json 을 수정하거나 다른 JSON 경로를 지정하세요.")
        return 1

    paths = run_pipeline(
        args.config,
        server=args.server,
        save_dir=args.out,
        seed_override=args.seed,
        denoise_override=args.denoise,
        ckpt_override=args.ckpt,
    )
    print("저장된 이미지:", paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
