import torch, os
from diffusers import StableDiffusionPipeline
from peft import PeftModel

MODEL_PATH = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AOM3A1B_orangemixs.safetensors"
LORA_PATH  = r"C:\Users\Violet\.claude\yukibot\lora\yuki_lora"
OUT_DIR    = r"C:\Users\Violet\.claude\yukibot\eye_compare"

PROMPT = (
    "masterpiece, best quality, yukixue, "
    "1girl, solo, long straight black hair, natural center part, "
    "pale cold white skin, oval face, thin lips, "
    "calm serene expression, looking at viewer, "
    "(cold grey eyes:1.5), (silver grey iris:1.3), cool grey pupils, "
    "detailed eyes, clear eye color, "
    "upper body close-up, soft neutral light, simple background"
)

NEGATIVE = (
    "worst quality, low quality, bad anatomy, deformed face, "
    "blurry eyes, closed eyes, amber eyes, brown eyes, yellow eyes, "
    "white hair, grey hair, silver hair, "
    "nsfw, loli, childish, text, watermark"
)

pipe = StableDiffusionPipeline.from_single_file(
    MODEL_PATH, torch_dtype=torch.float16, safety_checker=None,
)
pipe.unet = PeftModel.from_pretrained(pipe.unet, LORA_PATH)
pipe.unet = pipe.unet.merge_and_unload()
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

gen = torch.Generator("cuda").manual_seed(303)
result = pipe(
    prompt=PROMPT, negative_prompt=NEGATIVE,
    width=512, height=512,
    num_inference_steps=35, guidance_scale=8.5, generator=gen,
)
out = os.path.join(OUT_DIR, "cold_grey_lora_test.png")
result.images[0].save(out)
print(f"保存：{out}")

del pipe
torch.cuda.empty_cache()
