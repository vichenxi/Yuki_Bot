# LoRA 训练环境初始化
# 运行一次即可；后续直接用 2_train.ps1

$SD_PYTHON = "D:\Users\Violet\anaconda3\envs\sd\python.exe"
$SD_PIP    = "D:\Users\Violet\anaconda3\envs\sd\Scripts\pip.exe"
$SD_SCRIPTS = "E:\sd-scripts"

Write-Host "== 1. 克隆 sd-scripts =="
if (Test-Path $SD_SCRIPTS) {
    Write-Host "已存在，跳过克隆，执行 git pull..."
    git -C $SD_SCRIPTS pull
} else {
    git clone --depth 1 https://github.com/kohya-ss/sd-scripts.git $SD_SCRIPTS
}

Write-Host "== 2. 安装依赖到 sd 环境 =="
& $SD_PIP install --upgrade pip
Push-Location $SD_SCRIPTS
& $SD_PIP install -r requirements.txt
Pop-Location

Write-Host "== 3. 配置 accelerate（非交互，单 GPU） =="
$accel_cfg = "D:\Users\Violet\anaconda3\envs\sd\Lib\site-packages\accelerate\default_config.yaml"
@"
compute_environment: LOCAL_MACHINE
distributed_type: 'NO'
downcast_bf16: 'no'
machine_rank: 0
main_training_function: main
mixed_precision: fp16
num_machines: 1
num_processes: 1
use_cpu: false
"@ | Out-File -Encoding utf8 $accel_cfg

Write-Host ""
Write-Host "== 完成！接下来运行 2_train.ps1 =="
