# LoRA training pipeline
# Prerequisites: 1_setup.ps1 run once, admin service on localhost:8765

$env:PYTHONIOENCODING = "utf-8"
$OutputEncoding = [System.Text.UTF8Encoding]::new()

$SD_PYTHON   = "D:\Users\Violet\anaconda3\envs\sd\python.exe"
$SD_SCRIPTS  = "E:\sd-scripts"
$BASE_MODEL  = "E:\stable-diffusion-webui\models\Stable-diffusion\AOM3A1B_orangemixs.safetensors"
$OUT_DIR     = "F:\bot\data\lora\output"
$LOG_DIR     = "F:\bot\data\lora\logs"
$DATA_DIR    = "F:\bot\data\yuki_lora\img\20_yukixue"
$DATASET_CFG = "F:\bot\lora\dataset_config.toml"
$OUTPUT_NAME = "yuki_lora_v2_aom3"

# ── Step 1: Render training data ─────────────────────────────
Write-Host "== Step 1: Rendering VRM training data =="
& $SD_PYTHON "F:\bot\lora\gen_data.py"
if ($LASTEXITCODE -ne 0) { Write-Error "Render failed, aborting"; exit 1 }

$img_count = (Get-ChildItem $DATA_DIR -Filter "*.png").Count
Write-Host "Images generated: $img_count"
if ($img_count -eq 0) { Write-Error "No images found, aborting"; exit 1 }

# ── Step 2: Train LoRA ────────────────────────────────────────
Write-Host ""
Write-Host "== Step 2: Starting LoRA training =="

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$log_file  = "$LOG_DIR\train_$timestamp.log"

& $SD_PYTHON "$SD_SCRIPTS\train_network.py" `
  --pretrained_model_name_or_path="$BASE_MODEL" `
  --dataset_config="$DATASET_CFG" `
  --output_dir="$OUT_DIR" `
  --output_name="$OUTPUT_NAME" `
  --logging_dir="$LOG_DIR" `
  --log_prefix="yuki_" `
  --network_module="networks.lora" `
  --network_dim=32 `
  --network_alpha=16 `
  --learning_rate=1e-4 `
  --text_encoder_lr=5e-5 `
  --lr_scheduler="cosine_with_restarts" `
  --lr_warmup_steps=50 `
  --max_train_epochs=30 `
  --train_batch_size=2 `
  --save_every_n_epochs=5 `
  --mixed_precision="fp16" `
  --save_precision="fp16" `
  --gradient_checkpointing `
  --cache_latents `
  --cache_latents_to_disk `
  --clip_skip=1 `
  --seed=42 `
  --enable_bucket `
  --min_bucket_reso=256 `
  --max_bucket_reso=1024 2>&1 | Tee-Object -FilePath $log_file

if ($LASTEXITCODE -ne 0) {
    Write-Error "Training failed. Check log: $log_file"
    exit 1
}

Write-Host ""
Write-Host "== Done! LoRA saved to $OUT_DIR\$OUTPUT_NAME.safetensors =="
Write-Host "Log: $log_file"
