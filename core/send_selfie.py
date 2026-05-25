"""生成雪的户外自拍并发给薰"""
import torch, os, tempfile, json, urllib.request
from pathlib import Path
from diffusers import StableDiffusionPipeline
from peft import PeftModel

BASE        = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE / "config.json"

with open(CONFIG_PATH, encoding="utf-8") as f:
    _cfg = json.load(f)

def _resolve(p: str) -> str:
    return str((BASE / p).resolve()) if p and not Path(p).is_absolute() else p

MODEL_PATH = _resolve(_cfg.get("sd_model_path", ""))
LORA_PATH  = _resolve(_cfg.get("lora_path", "./lora/yuki_lora"))

PROMPT = (
    "yukixue, 1girl, solo, "
    "long straight black hair, natural center part, "
    "pale cold white skin, oval face, thin lips, "
    "(cold grey eyes:1.5), silver grey iris, "
    "calm slight smile, looking at viewer, "
    "outdoor park, sunny day, natural light, "
    "dark midi skirt, simple dark top, "
    "full body, standing, elegant posture"
)
NEGATIVE = (
    "worst quality, low quality, "
    "bad anatomy, bad proportions, deformed body, extra limbs, "
    "fused fingers, bad hands, floating limbs, "
    "blurry, nsfw, loli, childish, text, watermark, "
    "amber eyes, brown eyes, yellow eyes, white hair, grey hair, silver hair"
)

print("加载模型...")
pipe = StableDiffusionPipeline.from_single_file(
    MODEL_PATH, torch_dtype=torch.float16, safety_checker=None
)
pipe.unet = PeftModel.from_pretrained(pipe.unet, LORA_PATH)
pipe.unet = pipe.unet.merge_and_unload()
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

gen = torch.Generator("cuda").manual_seed(42)
print("生成中...")
result = pipe(
    prompt=PROMPT, negative_prompt=NEGATIVE,
    width=512, height=768,
    num_inference_steps=30, guidance_scale=7.5, generator=gen,
)

with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
    tmp_path = tmp.name
result.images[0].save(tmp_path)
del pipe
torch.cuda.empty_cache()
print("生成完成，发送中...")

token    = _cfg["bot_token"]
chat_id  = str(_cfg["default_chat_id"])
boundary = "yuki_boundary_xyz"

def part(name, val):
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
        f"{val}\r\n"
    ).encode("utf-8")

with open(tmp_path, "rb") as f:
    img = f.read()

body = part("chat_id", chat_id)
body += (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="photo"; filename="selfie.png"\r\n'
    f"Content-Type: image/png\r\n\r\n"
).encode()
body += img
body += f"\r\n--{boundary}--\r\n".encode()

req = urllib.request.Request(
    f"https://api.telegram.org/bot{token}/sendPhoto",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
)
with urllib.request.urlopen(req, timeout=30) as resp:
    r = json.loads(resp.read())
    print("图片发送:", r.get("ok"))

os.unlink(tmp_path)
print("完成")
