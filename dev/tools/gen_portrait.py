"""Generate Yuki portrait and save to profiles dir for admin panel."""
import torch
from pathlib import Path
from diffusers import StableDiffusionPipeline
from peft import PeftModel

MODEL_PATH   = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AOM3A1B_orangemixs.safetensors"
LORA_PATH    = r"C:\Users\Violet\.claude\yukibot\lora\yuki_lora"
PROFILES_DIR = Path(r"C:\Users\Violet\.claude\yukibot\data\profiles")
PROFILES_DIR.mkdir(parents=True, exist_ok=True)

PROMPT = (
    "yukixue, 1girl, solo, "
    "long straight black hair, natural center part, "
    "pale cold white skin, oval face, thin lips, "
    "(cold grey eyes:1.5), silver grey iris, "
    "calm slight smile, looking at viewer, "
    "simple dark background, soft indoor light, "
    "dark midi skirt, simple dark fitted top, "
    "full body, standing, elegant posture"
)
NEGATIVE = (
    "worst quality, low quality, "
    "bad anatomy, bad proportions, deformed body, extra limbs, "
    "fused fingers, bad hands, floating limbs, "
    "blurry, nsfw, loli, childish, text, watermark, "
    "amber eyes, brown eyes, yellow eyes, white hair, grey hair, silver hair"
)

print("loading model...")
pipe = StableDiffusionPipeline.from_single_file(
    MODEL_PATH, torch_dtype=torch.float16, safety_checker=None
)
pipe.unet = PeftModel.from_pretrained(pipe.unet, LORA_PATH)
pipe.unet = pipe.unet.merge_and_unload()
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

gen = torch.Generator("cuda").manual_seed(303)
print("generating...")
result = pipe(
    prompt=PROMPT, negative_prompt=NEGATIVE,
    width=512, height=768,
    num_inference_steps=30, guidance_scale=7.5,
    generator=gen,
)

out = PROFILES_DIR / "portrait.png"
result.images[0].save(out)
del pipe
torch.cuda.empty_cache()
print(f"saved → {out}")
