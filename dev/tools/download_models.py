"""
下载三个二次元 SD 模型到 SD WebUI 目录
使用 hf-mirror.com 国内镜像
"""
import urllib.request
import os
import sys
import time

DEST = r"E:\stable-diffusion-webui\models\Stable-Diffusion"

MODELS = [
    {
        "name": "AnythingV5",
        "url": "https://hf-mirror.com/ckpt/anything-v5.0/resolve/main/AnythingV5V3_v5PrtRE.safetensors",
        "filename": "AnythingV5_v5PrtRE.safetensors",
    },
    {
        "name": "Counterfeit-V3.0-fix-fp16",
        "url": "https://hf-mirror.com/gsdf/Counterfeit-V3.0/resolve/main/Counterfeit-V3.0_fix_fp16.safetensors",
        "filename": "Counterfeit-V3.0_fix_fp16.safetensors",
    },
    {
        "name": "AbyssOrangeMix3-A1B",
        "url": "https://hf-mirror.com/WarriorMama777/OrangeMixs/resolve/main/Models/AbyssOrangeMix3/AOM3A1B_orangemixs.safetensors",
        "filename": "AOM3A1B_orangemixs.safetensors",
    },
]


def download(name, url, dest_path):
    tmp_path = dest_path + ".tmp"
    start = time.time()

    # 支持断点续传
    resume_pos = 0
    if os.path.exists(tmp_path):
        resume_pos = os.path.getsize(tmp_path)
        print(f"[{name}] 断点续传，从 {resume_pos // 1024 // 1024} MB 继续")

    req = urllib.request.Request(url)
    if resume_pos:
        req.add_header("Range", f"bytes={resume_pos}-")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0)) + resume_pos
            total_mb = total / 1024 / 1024

            with open(tmp_path, "ab") as f:
                downloaded = resume_pos
                last_print = time.time()
                while True:
                    chunk = resp.read(1024 * 1024)  # 1MB chunks
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    now = time.time()
                    if now - last_print >= 10:
                        pct = downloaded / total * 100 if total else 0
                        speed = (downloaded - resume_pos) / (now - start) / 1024 / 1024
                        print(f"[{name}] {downloaded//1024//1024:.0f}/{total_mb:.0f} MB  {pct:.1f}%  {speed:.1f} MB/s")
                        last_print = now

        os.replace(tmp_path, dest_path)
        elapsed = time.time() - start
        print(f"[{name}] 完成！耗时 {elapsed:.0f}s")
        return True

    except Exception as e:
        print(f"[{name}] 失败：{e}")
        return False


def main():
    os.makedirs(DEST, exist_ok=True)
    for m in MODELS:
        dest = os.path.join(DEST, m["filename"])
        if os.path.exists(dest):
            print(f"[{m['name']}] 已存在，跳过")
            continue
        print(f"\n=== 开始下载 {m['name']} ===")
        download(m["name"], m["url"], dest)

    print("\n全部完成")


if __name__ == "__main__":
    main()
