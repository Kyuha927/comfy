import json
import sys
import os
import traceback
from pathlib import Path
from typing import List, Optional

# Add current dir to path to import run_character_pipeline and comfy_workflow
sys.path.append(os.path.abspath("."))
import run_character_pipeline as pipeline
import comfy_workflow as cw

# Set 1: Refined LoRA v2 (Selectable: Contact Shadows, material breaks, CFG 6.0) -> Seeds 800-802
EXECUTION_PLAN = [
    {"config": "configs/lora_test_bg_v2.json", "seeds": [800, 801, 802]}
]

def run_lora_pipeline(config_path: Path, seed: int):
    config = pipeline.load_config(config_path)
    base = config.get("base_character", {})
    
    prompt = pipeline.build_prompt_from_config(config)
    prefix = pipeline.build_filename_prefix(config)
    negative = config.get("negative_prompt", "")
    
    lora_name = base.get("lora_name")
    
    if lora_name:
        # Standard LoRA Flow
        verified_loras = {
            "Game Character Sprites v1.0.safetensors": "pixel_character_sprite_Illustrious.safetensors",
            "JJ's Isometric Room XL v1.0.safetensors": "JJsIsometricRoom_XL.safetensors",
            "SDXL Chibi Avatar Generator v1.0.safetensors": "chibi_avatar.safetensors"
        }
        target_lora = verified_loras.get(lora_name, lora_name)

        wf_config = {
            "modes": ["pixel_character", "lora_loader"],
            "placeholders": {
                "__PROMPT__": prompt,
                "__NEGATIVE__": negative,
                "__SEED__": seed,
                "__CKPT_NAME__": base.get("ckpt_name"),
                "__FILENAME_PREFIX__": prefix,
                "__WIDTH__": base.get("width", 1024),
                "__HEIGHT__": base.get("height", 1024),
                "__STEPS__": base.get("steps", 30),
                "__CFG__": base.get("cfg", 7.0),
                "__SAMPLER__": base.get("sampler_name", "dpmpp_2m"),
                "__SCHEDULER__": base.get("scheduler", "karras"),
                
                "__LORA_NAME__": target_lora,
                "__LORA_STRENGTH__": base.get("lora_weight", 0.7),
                "__MODEL_INPUT__": ["4", 0], 
                "__CLIP_INPUT__": ["4", 1],
            }
        }
        workflow = cw.build_workflow(wf_config)
        cw.connect(workflow, "1001", "3", "model", 0)
        cw.connect(workflow, "1001", "6", "clip", 1)
        cw.connect(workflow, "1001", "7", "clip", 1)
        cw.connect(workflow, "4", "8", "vae", 2)
    else:
        # No LoRA Flow
        wf_config = {
            "modes": ["pixel_character"],
            "placeholders": {
                "__PROMPT__": prompt,
                "__NEGATIVE__": negative,
                "__SEED__": seed,
                "__CKPT_NAME__": base.get("ckpt_name"),
                "__FILENAME_PREFIX__": prefix,
                "__WIDTH__": base.get("width", 1024),
                "__HEIGHT__": base.get("height", 1024),
                "__STEPS__": base.get("steps", 40),
                "__CFG__": base.get("cfg", 7.0),
                "__SAMPLER__": base.get("sampler_name", "dpmpp_2m"),
                "__SCHEDULER__": base.get("scheduler", "karras")
            }
        }
        workflow = cw.build_workflow(wf_config)
        # Ensure VAEDecode uses built-in VAE
        cw.connect(workflow, "4", "8", "vae", 2)

    # Execute
    try:
        abs_outputs = Path(__file__).resolve().parent / "outputs"
        abs_outputs.mkdir(parents=True, exist_ok=True)
        paths = cw.generate_image(workflow, save_dir=abs_outputs)
    except Exception as e:
        with open("failed_workflow.json", "w", encoding="utf-8") as f:
            json.dump(workflow, f, indent=2)
        print(f"Saved failed_workflow.json for debug. Error: {e}")
        raise e
    
    # Metadata logging (Rule #1)
    meta = {
        "lora_name": target_lora if lora_name else "NONE",
        "lora_weight": base.get("lora_weight", 0.0),
        "ckpt_name": base.get("ckpt_name"),
        "seed": seed,
        "prompt": prompt,
        "steps": base.get("steps"),
        "cfg": base.get("cfg"),
        "resolution": f"{base.get('width')}x{base.get('height')}"
    }
    for p in paths:
        meta_path = p.with_suffix(".metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
            
    return paths

def main():
    root = Path(__file__).resolve().parent
    total = sum(len(x["seeds"]) for x in EXECUTION_PLAN)
    count_run = 0
    success_run = 0
    
    print(f"Starting Comparative Background Test ({total} images total)")
    for entry in EXECUTION_PLAN:
        cfg_rel = entry["config"]
        cfg_path = root / cfg_rel
        for seed in entry["seeds"]:
            count_run += 1
            print(f"[{count_run}/{total}] Processing {cfg_rel} Seed={seed} ...")
            try:
                paths = run_lora_pipeline(cfg_path, seed)
                print(f"  -> Success: {[p.name for p in paths]}")
                success_run += 1
            except Exception as e:
                print(f"  -> FAILED: {e}")
                traceback.print_exc()
                
    print(f"\nDone. Success: {success_run}/{total}")

if __name__ == "__main__":
    main()
