"""
雪 LoRA 训练脚本
- 基础模型：AOM3A1B_orangemixs.safetensors
- 训练集：基准模型图/（48张）
- epoch：10
- 学习率：1e-4
- LoRA rank：16, alpha：16
- 输出：lora/yuki_lora.safetensors
"""
import os, math, torch
from pathlib import Path
from PIL import Image
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from diffusers import StableDiffusionPipeline, DDPMScheduler
from diffusers.loaders import AttnProcsLayers
from diffusers.models.attention_processor import LoRAAttnProcessor
from peft import LoraConfig, get_peft_model
from transformers import CLIPTokenizer, CLIPTextModel
from accelerate import Accelerator
from tqdm.auto import tqdm

# ── 路径 ────────────────────────────────────────────────────────────
MODEL_PATH   = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AOM3A1B_orangemixs.safetensors"
TRAIN_DIR    = r"C:\Users\Violet\.claude\yukibot\基准模型图"
OUT_DIR      = r"C:\Users\Violet\.claude\yukibot\lora"
os.makedirs(OUT_DIR, exist_ok=True)

# ── 超参数 ──────────────────────────────────────────────────────────
INSTANCE_PROMPT = (
    "yukixue, 1girl, long straight black hair, pale cold white skin, "
    "oval face, thin lips, calm expression, slim elegant"
)
RESOLUTION  = 512
BATCH_SIZE  = 1
NUM_EPOCHS  = 10
LR          = 1e-4
LORA_RANK   = 16
LORA_ALPHA  = 16
GRAD_ACCUM  = 4
MIXED_PREC  = "fp16"

# ── 数据集 ──────────────────────────────────────────────────────────
class YukiDataset(Dataset):
    def __init__(self, img_dir, tokenizer, prompt, size=512):
        self.imgs = [p for p in Path(img_dir).iterdir()
                     if p.suffix.lower() in (".png", ".jpg", ".jpeg")]
        self.tokenizer = tokenizer
        self.prompt = prompt
        self.tf = transforms.Compose([
            transforms.Resize(size, interpolation=transforms.InterpolationMode.BILINEAR),
            transforms.CenterCrop(size),
            transforms.ToTensor(),
            transforms.Normalize([0.5], [0.5]),
        ])

    def __len__(self):
        return len(self.imgs)

    def __getitem__(self, idx):
        img = Image.open(self.imgs[idx]).convert("RGB")
        pixel = self.tf(img)
        ids = self.tokenizer(
            self.prompt,
            padding="max_length",
            truncation=True,
            max_length=self.tokenizer.model_max_length,
            return_tensors="pt",
        ).input_ids[0]
        return {"pixel_values": pixel, "input_ids": ids}

# ── 主流程 ──────────────────────────────────────────────────────────
def main():
    accelerator = Accelerator(mixed_precision=MIXED_PREC, gradient_accumulation_steps=GRAD_ACCUM)

    print("加载模型...")
    pipe = StableDiffusionPipeline.from_single_file(
        MODEL_PATH, torch_dtype=torch.float32, safety_checker=None,
    )
    tokenizer   = pipe.tokenizer
    text_encoder = pipe.text_encoder
    vae          = pipe.vae
    unet         = pipe.unet
    noise_scheduler = DDPMScheduler.from_config(pipe.scheduler.config)

    vae.requires_grad_(False)
    text_encoder.requires_grad_(False)

    # LoRA on unet attention layers
    lora_config = LoraConfig(
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        target_modules=["to_q", "to_k", "to_v", "to_out.0"],
        lora_dropout=0.1,
    )
    unet = get_peft_model(unet, lora_config)
    unet.print_trainable_parameters()

    optimizer = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, unet.parameters()), lr=LR
    )

    dataset = YukiDataset(TRAIN_DIR, tokenizer, INSTANCE_PROMPT, RESOLUTION)
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    lr_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=NUM_EPOCHS * math.ceil(len(dataloader) / GRAD_ACCUM)
    )

    unet, optimizer, dataloader, lr_scheduler = accelerator.prepare(
        unet, optimizer, dataloader, lr_scheduler
    )
    vae          = vae.to(accelerator.device, dtype=torch.float16)
    text_encoder = text_encoder.to(accelerator.device)

    print(f"\n开始训练：{len(dataset)} 张图，{NUM_EPOCHS} epoch，LR={LR}")

    for epoch in range(NUM_EPOCHS):
        unet.train()
        epoch_loss = 0.0
        pbar = tqdm(dataloader, desc=f"Epoch {epoch+1}/{NUM_EPOCHS}")
        for step, batch in enumerate(pbar):
            with accelerator.accumulate(unet):
                latents = vae.encode(
                    batch["pixel_values"].to(dtype=torch.float16)
                ).latent_dist.sample() * 0.18215

                noise = torch.randn_like(latents)
                timesteps = torch.randint(
                    0, noise_scheduler.config.num_train_timesteps,
                    (latents.shape[0],), device=latents.device
                ).long()
                noisy_latents = noise_scheduler.add_noise(latents, noise, timesteps)

                encoder_hidden = text_encoder(batch["input_ids"])[0]
                model_pred = unet(noisy_latents, timesteps, encoder_hidden).sample

                if noise_scheduler.config.prediction_type == "epsilon":
                    target = noise
                else:
                    target = noise_scheduler.get_velocity(latents, noise, timesteps)

                loss = torch.nn.functional.mse_loss(
                    model_pred.float(), target.float(), reduction="mean"
                )
                accelerator.backward(loss)
                optimizer.step()
                lr_scheduler.step()
                optimizer.zero_grad()

            epoch_loss += loss.detach().item()
            pbar.set_postfix(loss=f"{loss.item():.4f}")

        avg = epoch_loss / len(dataloader)
        print(f"Epoch {epoch+1} avg loss: {avg:.4f}")

    # 保存 LoRA 权重
    accelerator.wait_for_everyone()
    unwrapped = accelerator.unwrap_model(unet)
    lora_path = os.path.join(OUT_DIR, "yuki_lora")
    unwrapped.save_pretrained(lora_path)
    print(f"\n训练完成，LoRA 保存至：{lora_path}")

if __name__ == "__main__":
    main()
