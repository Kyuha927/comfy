import json
import sys
import os
import traceback
from pathlib import Path

# Add current dir to path
sys.path.append(os.path.abspath("."))
import run_character_pipeline as pipeline
import comfy_workflow as cw

# Execution Plan for Standard Prototype (BG + Objects) + Specialization
EXECUTION_PLAN = [
    {"config": "configs/bg_empty_refined.json", "seeds": [900]},
    {"config": "configs/lora_test_flat_assets.json", "seeds": [900]},
    {"config": "configs/lora_test_pixel_items.json", "seeds": [900]}
]

def run_lora_pipeline(config_path: Path, seed: int):
    config = pipeline.load_config(config_path)
    base = config.get("base_character", {})
    
    prompt = pipeline.build_prompt_from_config(config)
    prefix = pipeline.build_filename_prefix(config)
    negative = config.get("negative_prompt", "")
    
    lora_name = base.get("lora_name")
    
    if lora_name:
        verified_loras = {
            "JJ's Isometric Room XL v1.0.safetensors": "JJsIsometricRoom_XL.safetensors"
        }
        target_lora = verified_loras.get(lora_name, lora_name)

        wf_config = {
            "modes": ["pixel_character", "lora_loader"],
            "placeholders": {
                "__PROMPT__": prompt,
                "__NEGATIVE__": negative,
                "__SEED__": seed,
                "__CKPT_NAME__": base.get("ckpt_name"),
                "__FILENAME_PREFIX__": f"proto_{prefix}",
                "__WIDTH__": base.get("width", 1024),
                "__HEIGHT__": base.get("height", 1024),
                "__STEPS__": base.get("steps", 32),
                "__CFG__": base.get("cfg", 6.0),
                "__SAMPLER__": base.get("sampler_name", "dpmpp_2m"),
                "__SCHEDULER__": base.get("scheduler", "karras"),
                
                "__LORA_NAME__": target_lora,
                "__LORA_STRENGTH__": base.get("lora_weight", 0.45),
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
        wf_config = {
            "modes": ["pixel_character"],
            "placeholders": {
                "__PROMPT__": prompt,
                "__NEGATIVE__": negative,
                "__SEED__": seed,
                "__CKPT_NAME__": base.get("ckpt_name"),
                "__FILENAME_PREFIX__": f"proto_{prefix}",
                "__WIDTH__": base.get("width", 1024),
                "__HEIGHT__": base.get("height", 1024),
                "__STEPS__": base.get("steps", 32),
                "__CFG__": base.get("cfg", 6.0),
                "__SAMPLER__": base.get("sampler_name", "dpmpp_2m"),
                "__SCHEDULER__": base.get("scheduler", "karras")
            }
        }
        workflow = cw.build_workflow(wf_config)
        cw.connect(workflow, "4", "8", "vae", 2)

    try:
        abs_outputs = Path(r"c:\Users\jhk92\OneDrive\문서\GitHub\comfy\outputs")
        abs_outputs.mkdir(parents=True, exist_ok=True)
        paths = cw.generate_image(workflow, save_dir=abs_outputs)
        
        # Save Metadata
        meta = {
            "config": config_path.name,
            "seed": seed,
            "prompt": prompt,
            "lora_weight": base.get("lora_weight")
        }
        for p in paths:
            meta_p = p.with_suffix(".metadata.json")
            with open(meta_p, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)
        return paths
    except Exception as e:
        print(f"Failed: {e}")
        return []

def main():
    root = Path(__file__).resolve().parent
    for entry in EXECUTION_PLAN:
        cfg_path = root / entry["config"]
        for seed in entry["seeds"]:
            print(f"Generating {cfg_path.name} (Seed {seed})...")
            run_lora_pipeline(cfg_path, seed)

if __name__ == "__main__":
    main()
