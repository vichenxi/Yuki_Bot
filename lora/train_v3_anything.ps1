$env:PYTHONIOENCODING = "utf-8"
$OutputEncoding = [System.Text.UTF8Encoding]::new()

$SD_PYTHON   = "D:\Users\Violet\anaconda3\envs\sd\python.exe"
$SD_SCRIPTS  = "E:\sd-scripts"
$BASE_MODEL  = "E:\stable-diffusion-webui\models\Stable-diffusion\AnythingV5_v5PrtRE.safetensors"
$OUT_DIR     = "F:\bot\data\lora\output"
$LOG_DIR     = "F:\bot\data\lora\logs"
$DATASET_CFG = "F:\bot\lora\dataset_config.toml"
$OUTPUT_NAME = "yuki_lora_v3_anything"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$log_file  = "$LOG_DIR\train_v3_anything_$timestamp.log"

Write-Host "== Training V3 — AnythingV5 base =="

& $SD_PYTHON "$SD_SCRIPTS\train_network.py" `
  --pretrained_model_name_or_path="$BASE_MODEL" `
  --dataset_config="$DATASET_CFG" `
  --output_dir="$OUT_DIR" `
  --output_name="$OUTPUT_NAME" `
  --logging_dir="$LOG_DIR" `
  --log_prefix="yuki_v3_any_" `
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

if ($LASTEXITCODE -ne 0) { Write-Error "Failed. Log: $log_file"; exit 1 }
Write-Host "== Done: $OUT_DIR\$OUTPUT_NAME.safetensors =="
