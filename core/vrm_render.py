"""
从 VRM 模型生成参考图像。

用法：
  python vrm_render.py <输出路径.png> [--angle <0-360>] [--bust]

依赖 admin 服务 (localhost:8765) 已在运行，通过 /model/vrm 端点取模型。
使用 playwright 无头渲染，首次需：pip install playwright && python -m playwright install chromium
"""
import sys
import json
import argparse
import tempfile
import urllib.request
from pathlib import Path

ADMIN_URL = "http://127.0.0.1:8765"
VRM_URL   = f"{ADMIN_URL}/model/vrm"

# Headless renderer HTML — inlines the VRM viewer, renders one frame, captures canvas
_RENDERER_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<script type="importmap">
{{
  "imports": {{
    "three": "{base}/static/three/build/three.module.js",
    "three/addons/": "{base}/static/three/examples/jsm/",
    "@pixiv/three-vrm": "{base}/static/three-vrm/three-vrm.module.min.js"
  }}
}}
</script>
</head>
<body style="margin:0;background:#0d0d0d">
<canvas id="c" width="{w}" height="{h}"></canvas>
<script type="module">
import * as THREE from 'three';
import {{ GLTFLoader }} from 'three/addons/loaders/GLTFLoader.js';
import {{ VRMLoaderPlugin, VRMUtils }} from '@pixiv/three-vrm';

async function run() {{
  const canvas = document.getElementById('c');
  const renderer = new THREE.WebGLRenderer({{ canvas, antialias: true }});
  renderer.setSize({w}, {h});
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.setClearColor(0x0d0d0d, 1);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(25, {w}/{h}, 0.1, 100);

  scene.add(new THREE.AmbientLight(0xffffff, 1.1));
  const sun = new THREE.DirectionalLight(0xffffff, 1.35);
  sun.position.set(1.5, 3, 2); scene.add(sun);
  const fill = new THREE.DirectionalLight(0xeef4ff, 0.55);
  fill.position.set(-2, 1, -1); scene.add(fill);

  const loader = new GLTFLoader();
  loader.register(p => new VRMLoaderPlugin(p));

  const gltf = await loader.loadAsync('{vrm_url}');
  const vrm = gltf.userData.vrm;
  if (vrm.meta?.metaVersion === '0' || !vrm.meta?.metaVersion) VRMUtils.rotateVRM0(vrm);

  // Natural resting arm pose (from desktop app.js: Z negative=left arm down, positive=right arm down)
  const lArm = vrm.humanoid.getNormalizedBoneNode('leftUpperArm');
  const rArm = vrm.humanoid.getNormalizedBoneNode('rightUpperArm');
  if (lArm) {{ lArm.rotation.x = 0.10; lArm.rotation.y = 0; lArm.rotation.z = -1.25; }}
  if (rArm) {{ rArm.rotation.x = 0.10; rArm.rotation.y = 0; rArm.rotation.z =  1.25; }}
  vrm.update(0);

  const box = new THREE.Box3().setFromObject(vrm.scene);
  vrm.scene.position.x -= (box.max.x + box.min.x) / 2;
  vrm.scene.position.y -= box.min.y;

  const modelH = box.max.y - box.min.y;
  const midY = modelH / 2;
  const fovRad = 25 * Math.PI / 180;
  const fitZ = (modelH / 2 * ({bust} ? 0.55 : 1.15)) / Math.tan(fovRad / 2);

  // Rotate around Y axis by angle
  const angle = {angle} * Math.PI / 180;
  camera.position.set(Math.sin(angle) * fitZ, midY * ({bust} ? 1.35 : 0.9), Math.cos(angle) * fitZ);
  camera.lookAt(0, midY * ({bust} ? 1.35 : 0.85), 0);

  scene.add(vrm.scene);
  renderer.render(scene, camera);

  window.__vrm_done__ = canvas.toDataURL('image/png');
}}
run().catch(e => {{ window.__vrm_error__ = String(e); }});
</script>
</body>
</html>"""


def render_vrm(output_path: str, angle: float = 0, bust: bool = False,
               width: int = 512, height: int = 768) -> bool:
    """Render VRM to PNG. Returns True on success."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[vrm_render] playwright not installed: pip install playwright && python -m playwright install chromium",
              file=sys.stderr)
        return False

    html = _RENDERER_HTML.format(
        base=ADMIN_URL, vrm_url=VRM_URL,
        w=width, h=height,
        angle=angle, bust="true" if bust else "false",
    )

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        f.write(html)
        tmp_html = f.name

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(f"file:///{tmp_html.replace(chr(92), '/')}")
            # Wait for render
            page.wait_for_function("window.__vrm_done__ || window.__vrm_error__", timeout=30000)
            err = page.evaluate("window.__vrm_error__")
            if err:
                print(f"[vrm_render] JS error: {err}", file=sys.stderr)
                browser.close()
                return False
            data_url = page.evaluate("window.__vrm_done__")
            browser.close()

        # Decode base64 and save
        import base64
        header, b64 = data_url.split(",", 1)
        Path(output_path).write_bytes(base64.b64decode(b64))
        print(f"[vrm_render] saved {output_path} ({width}×{height}, angle={angle}°)", file=sys.stderr)
        return True
    finally:
        Path(tmp_html).unlink(missing_ok=True)


def render_training_set(output_dir: str, count: int = 8) -> list[str]:
    """Render VRM from multiple angles for LoRA training data. Returns list of saved paths."""
    import math
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    angles = [i * (360 / count) for i in range(count)]
    for i, angle in enumerate(angles):
        p = str(out / f"yuki_{i:02d}_a{int(angle):03d}.png")
        ok = render_vrm(p, angle=angle, width=512, height=768)
        if ok:
            paths.append(p)
        # Also bust shots from front/3/4
        if angle in (0, 45, 315):
            bp = str(out / f"yuki_{i:02d}_a{int(angle):03d}_bust.png")
            ok2 = render_vrm(bp, angle=angle, bust=True, width=512, height=512)
            if ok2:
                paths.append(bp)
    return paths


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("output", nargs="?", default="vrm_render.png")
    ap.add_argument("--angle", type=float, default=0)
    ap.add_argument("--bust",  action="store_true")
    ap.add_argument("--training-set", metavar="DIR")
    ap.add_argument("--count", type=int, default=8)
    args = ap.parse_args()

    if args.training_set:
        paths = render_training_set(args.training_set, args.count)
        print(json.dumps({"ok": True, "count": len(paths), "paths": paths}))
    else:
        ok = render_vrm(args.output, angle=args.angle, bust=args.bust)
        sys.exit(0 if ok else 1)
