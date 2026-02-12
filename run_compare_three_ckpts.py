# -*- coding: utf-8 -*-
"""
Animagine XL 3.1, Illustrious-XL, Bulldozer BETA 3체크포인트 비교.
이전 AOM3A1 vs anything-v5와 동일한 프롬프트/설정, 시드 100·101·102 각 3장씩 생성.
ComfyUI에 없는 체크포인트는 건너뛰고, 사용 가능한 체크포인트만 사용합니다.
"""
from pathlib import Path
import run_character_pipeline as pipeline
import comfy_workflow as cw

CONFIG = Path(__file__).resolve().parent / "configs" / "compare_two_ckpts.json"
PREFERRED_CHECKPOINTS = [
    "animagine-xl-3.1.safetensors",
    "Illustrious-XL-v2.0.safetensors",
    "SDXLAnimeBulldozer_v20.safetensors",
]
SEEDS = [100, 101, 102]


def main():
    if not CONFIG.exists():
        print(f"설정 없음: {CONFIG}")
        return 1
    # ComfyUI에 실제로 있는 체크포인트만 사용
    try:
        available = cw.get_available_checkpoints(server=cw.DEFAULT_SERVER)
    except Exception as e:
        print(f"체크포인트 목록 조회 실패: {e}")
        available = []
    if available:
        checkpoints = [c for c in PREFERRED_CHECKPOINTS if c in available]
        if not checkpoints:
            checkpoints = available[:3]
            print(f"선호 체크포인트가 없어 사용 가능한 체크포인트 {checkpoints} 로 비교합니다.")
        elif len(checkpoints) < len(PREFERRED_CHECKPOINTS):
            missing = set(PREFERRED_CHECKPOINTS) - set(checkpoints)
            print(f"ComfyUI에 없어 건너뜀: {missing}")
    else:
        checkpoints = PREFERRED_CHECKPOINTS
        print("체크포인트 목록을 가져오지 못해 선호 목록 그대로 시도합니다.")
    total = len(checkpoints) * len(SEEDS)
    n = 0
    ok_count = 0
    fail_count = 0
    for ckpt in checkpoints:
        for seed in SEEDS:
            n += 1
            print(f"[{n}/{total}] {ckpt} seed={seed} ...")
            try:
                paths = pipeline.run_pipeline(
                    CONFIG,
                    seed_override=seed,
                    ckpt_override=ckpt,
                )
                if paths:
                    print(f"  -> {paths[0]}")
                    ok_count += 1
                else:
                    print("  -> (실패: 저장된 이미지 없음)")
                    fail_count += 1
            except Exception as e:
                print(f"  오류: {e}")
                fail_count += 1
    print("전체 완료. 성공:", ok_count, "실패:", fail_count)
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
