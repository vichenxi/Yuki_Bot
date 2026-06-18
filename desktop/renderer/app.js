import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { VRMLoaderPlugin, VRMUtils, VRMExpression, VRMExpressionMorphTargetBind } from '@pixiv/three-vrm'

const CANVAS_W = 380   // 固定画布宽度，Pose 面板在其右侧展开

// ── Renderer & Scene ──────────────────────────────────────────
const canvas = document.getElementById('canvas')

const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true })
renderer.setPixelRatio(window.devicePixelRatio)
renderer.setSize(CANVAS_W, window.innerHeight)
renderer.setClearColor(0x000000, 0)
renderer.outputColorSpace = THREE.SRGBColorSpace

const scene  = new THREE.Scene()
const camera = new THREE.PerspectiveCamera(25, CANVAS_W / window.innerHeight, 0.1, 100)

// Lighting
scene.add(new THREE.AmbientLight(0xffffff, 1.1))
const sun = new THREE.DirectionalLight(0xffffff, 1.35)
sun.position.set(1.5, 3, 2)
scene.add(sun)
const fill = new THREE.DirectionalLight(0xeef4ff, 0.55)
fill.position.set(-2, 1, -1)
scene.add(fill)

// ── 姿势参数（Pose 面板控制的全局值） ────────────────────────
const pose = {
  // 相机
  camZ:    5.0,
  camY:    0.9,
  lookY:   0.9,
  fov:     25,

  // 上半身
  spineX:  0.0,
  spineZ:  0.0,
  chestX:  0.0,

  // 手臂（Z 轴控制上下：负值=左臂下垂，正值=右臂下垂）
  lArmX:  0.10, lArmY:  0.0, lArmZ: -1.25,
  rArmX:  0.10, rArmY:  0.0, rArmZ:  1.25,
  lForeX: 0.0,
  rForeX: 0.0,
}

function updateCamera () {
  camera.position.set(0, pose.camY, pose.camZ)
  camera.fov = pose.fov
  camera.updateProjectionMatrix()
  camera.lookAt(0, pose.lookY, 0)
}
updateCamera()

// ── 视线追踪（直接操作骨骼，不依赖 vrm.lookAt） ──────────────
// gaze：当前平滑值；_gazeTgt：目标值（由鼠标设置）
const gaze    = { headY: 0, headX: 0, eyeY: 0, eyeX: 0 }
const _gazeTgt = { headY: 0, headX: 0, eyeY: 0, eyeX: 0 }

// 全屏视线跟随：以窗口中心为原点，用屏幕宽高归一化
window.yukiAPI.onCursor((cx, cy, wx, wy, ww, wh) => {
  const sw = window.screen.width, sh = window.screen.height
  const nx = (cx - (wx + ww / 2)) / (sw * 0.35)
  const ny = (cy - (wy + wh / 2)) / (sh * 0.35)
  const clamp = v => Math.max(-1, Math.min(1, v))
  _gazeTgt.headY =  clamp(nx) * 0.22
  _gazeTgt.headX =  clamp(ny) * 0.10
  _gazeTgt.eyeY  =  clamp(nx) * 0.12
  _gazeTgt.eyeX  =  clamp(ny) * 0.10
})

// ── VRM 加载 ──────────────────────────────────────────────────
let vrm = null
const clock = new THREE.Clock()
const loader = new GLTFLoader()
loader.register(p => new VRMLoaderPlugin(p))

async function loadVRM () {
  const vrmPath = await window.yukiAPI.getVRMPath()
  const url = 'file:///' + vrmPath.replace(/\\/g, '/')
  const gltf = await loader.loadAsync(url)
  vrm = gltf.userData.vrm

  if (vrm.meta?.metaVersion === '0' || !vrm.meta?.metaVersion) {
    VRMUtils.rotateVRM0(vrm)
  }

  // 底部对齐 y=0，水平居中
  const box = new THREE.Box3().setFromObject(vrm.scene)
  vrm.scene.position.x -= (box.max.x + box.min.x) / 2
  vrm.scene.position.y -= box.min.y

  // 自动适配相机以显示完整身体
  const modelH = box.max.y - box.min.y
  const midY   = modelH / 2
  const fovRad = pose.fov * Math.PI / 180
  // 需要多少距离才能看到完整高度（留 15% 上下余量）
  const fitZ   = (modelH / 2 * 1.15) / Math.tan(fovRad / 2)
  pose.camZ    = parseFloat(fitZ.toFixed(2))
  pose.camY    = parseFloat((midY * 0.9).toFixed(2))
  pose.lookY   = parseFloat((midY * 0.85).toFixed(2))
  updateCamera()

  scene.add(vrm.scene)
  console.log('[yuki] loaded:', vrm.meta?.name, `| H=${modelH.toFixed(2)}m | fitZ=${fitZ.toFixed(2)}`)

  // 注册 morph custom expressions（同名跨 mesh 合并）
  vrm.scene.traverse(obj => {
    if (!obj.isMesh || !obj.morphTargetDictionary) return
    for (const [name, idx] of Object.entries(obj.morphTargetDictionary)) {
      if (!morphGroups.has(name)) morphGroups.set(name, [])
      morphGroups.get(name).push({ mesh: obj, idx })
    }
  })
  if (vrm.expressionManager) {
    for (const [name, binds] of morphGroups) {
      const expr = new VRMExpression(`__m:${name}`)
      for (const { mesh, idx } of binds)
        expr.addBind(new VRMExpressionMorphTargetBind({ primitives: [mesh], index: idx, weight: 1.0 }))
      vrm.expressionManager.registerExpression(expr)
    }
  }

  // 面板已存在时同步相机滑块
  syncPanelValues()
}

loadVRM().catch(err => console.error('[yuki] VRM load error:', err))

// ── 眨眼 ──────────────────────────────────────────────────────
let blinkState = 'wait'
let blinkT = 0, blinkWait = rnd(3, 7)

function rnd (a, b) { return a + Math.random() * (b - a) }

function updateBlink (dt) {
  if (!vrm?.expressionManager) return
  switch (blinkState) {
    case 'wait':
      if ((blinkWait -= dt) <= 0) { blinkState = 'closing'; blinkT = 0 }
      break
    case 'closing':
      vrm.expressionManager.setValue('blink', Math.min((blinkT += dt / 0.07), 1))
      if (blinkT >= 1) { blinkState = 'opening'; blinkT = 0 }
      break
    case 'opening':
      vrm.expressionManager.setValue('blink', Math.max(1 - (blinkT += dt / 0.12), 0))
      if (blinkT >= 1) {
        vrm.expressionManager.setValue('blink', 0)
        blinkState = 'wait'
        blinkWait = rnd(3, 7)
      }
      break
  }
}

// ── 表情（平滑过渡） ─────────────────────────────────────────
const EXPR_NAMES  = ['happy', 'surprised', 'relaxed', 'sad', 'angry']
const exprWeights = Object.fromEntries(EXPR_NAMES.map(n => [n, 0]))
const exprTargets = Object.fromEntries(EXPR_NAMES.map(n => [n, 0]))
const EXPR_SPEED  = 6.0   // 约 0.15s 完成过渡

const CLICK_CYCLE = ['happy', 'surprised', 'relaxed']
let clickIdx = 0, exprTimer = 0

const MOOD_MAP = {
  happy:   { e: 'happy',     i: 0.75 },
  excited: { e: 'surprised', i: 0.65 },
  sad:     { e: 'sad',       i: 0.55 },
  angry:   { e: 'angry',     i: 0.50 },
  calm:    { e: 'relaxed',   i: 0.55 },
  relaxed: { e: 'relaxed',   i: 0.55 },
}

function setExprTarget (name, intensity = 0.9) {
  EXPR_NAMES.forEach(n => { exprTargets[n] = (n === name) ? intensity : 0 })
}
function applyExpr (name, intensity = 0.9, duration = 2.5) {
  setExprTarget(name, intensity)
  exprTimer = duration
}
function clearExpr () { setExprTarget(null) }
function updateExpressions (dt) {
  if (!vrm?.expressionManager) return
  for (const name of EXPR_NAMES) {
    exprWeights[name] += (exprTargets[name] - exprWeights[name]) * Math.min(1, EXPR_SPEED * dt)
    vrm.expressionManager.setValue(name, exprWeights[name])
  }
}

window.yukiAPI.onMood(m => {
  const e = MOOD_MAP[m]
  if (e) applyExpr(e.e, e.i, Infinity)
})

// ── Morph groups（VRM 加载后填充） ────────────────────────────
const morphGroups = new Map()   // name → [{mesh,idx}]

// ── 预设叠加 ──────────────────────────────────────────────────
// 只列 updateIdle 每帧实际写入的骨骼；其余骨骼走 lerp-to-0 路径
const IDLE_MANAGED = new Set([
  'hips', 'spine', 'chest',
  'head',
  'leftUpperArm',  'leftLowerArm',
  'rightUpperArm', 'rightLowerArm',
  'leftEye', 'rightEye',
])

let presetActive      = false
let presetBlend       = 0
let presetBoneTargets = {}
let presetMorphTargets = {}   // name → target weight

function applyPresetBlend (dt) {
  if (presetActive)  presetBlend = Math.min(1, presetBlend + dt * 3.5)
  else               presetBlend = Math.max(0, presetBlend - dt * 3.5)

  if (!vrm?.humanoid) return

  for (const [name, tgt] of Object.entries(presetBoneTargets)) {
    const bone = vrm.humanoid.getNormalizedBoneNode(name)
    if (!bone) continue

    if (IDLE_MANAGED.has(name)) {
      // updateIdle 已写完当帧 idle 值；presetBlend > 0 时向预设目标拉
      if (presetBlend > 0) {
        bone.rotation.x += (tgt.x - bone.rotation.x) * presetBlend
        bone.rotation.y += (tgt.y - bone.rotation.y) * presetBlend
        bone.rotation.z += (tgt.z - bone.rotation.z) * presetBlend
      }
    } else {
      // idle 不管的骨骼（手指等）：激活时向预设目标，清除时向 0，独立 lerp
      const tx = presetActive ? tgt.x : 0
      const ty = presetActive ? tgt.y : 0
      const tz = presetActive ? tgt.z : 0
      const s  = Math.min(dt * 5, 1)
      bone.rotation.x += (tx - bone.rotation.x) * s
      bone.rotation.y += (ty - bone.rotation.y) * s
      bone.rotation.z += (tz - bone.rotation.z) * s
    }
  }

  // blend 归零且预设已清除时，归零所有预设骨骼并清理 targets
  // idle-managed 骨骼在下一帧会被 updateIdle 立即覆写，单帧归零不可见
  if (presetBlend <= 0 && !presetActive) {
    for (const name of Object.keys(presetBoneTargets)) {
      const bone = vrm.humanoid.getNormalizedBoneNode(name)
      if (bone) { bone.rotation.x = 0; bone.rotation.y = 0; bone.rotation.z = 0 }
    }
    presetBoneTargets  = {}
    presetMorphTargets = {}
  }

  // morph：用同一 presetBlend 因子驱动，fade in/out 与骨骼同步
  if (vrm.expressionManager) {
    for (const name of morphGroups.keys()) {
      const target = presetMorphTargets[name] ?? 0
      vrm.expressionManager.setValue(`__m:${name}`, target * presetBlend)
    }
  }
}

window.yukiAPI.onPresetApply(preset => {
  if (!preset) {
    presetActive       = false
    presetMorphTargets = {}
    EXPR_NAMES.forEach(n => { exprTargets[n] = 0 })
    exprTimer = 0
    return
  }
  presetBoneTargets  = {}
  presetMorphTargets = {}
  for (const [name, v] of Object.entries(preset.bones ?? {}))
    presetBoneTargets[name] = { x: v[0], y: v[1], z: v[2] }
  for (const [name, val] of Object.entries(preset.morphs ?? {}))
    presetMorphTargets[name] = val
  EXPR_NAMES.forEach(n => { exprTargets[n] = 0 })
  for (const [name, val] of Object.entries(preset.expressions ?? {}))
    if (EXPR_NAMES.includes(name)) exprTargets[name] = val
  exprTimer = Infinity
  presetActive = true
})

// ── Idle 状态机（偶发行为） ───────────────────────────────────
const ism = {
  state:      'normal',   // 'normal' | 'lookaround' | 'returning'
  timer:      rnd(10, 20),
  headTargY:  0,
  headCurY:   0,
}

function updateISM (dt) {
  ism.timer -= dt

  if (ism.state === 'normal' && ism.timer <= 0) {
    ism.state    = 'lookaround'
    ism.headTargY = (Math.random() > 0.5 ? 1 : -1) * rnd(0.12, 0.26)
    ism.timer    = rnd(2.5, 5.0)    // 侧头保持时长
  } else if (ism.state === 'lookaround' && ism.timer <= 0) {
    ism.state    = 'returning'
    ism.headTargY = 0
    ism.timer    = rnd(12, 22)      // 下次触发等待
  } else if (ism.state === 'returning' && Math.abs(ism.headCurY) < 0.003) {
    ism.state = 'normal'
  }

  // 平滑插值到目标
  ism.headCurY += (ism.headTargY - ism.headCurY) * Math.min(dt * 1.8, 1)
}

// ── Idle 动画 ─────────────────────────────────────────────────
function sw (t, f, a, p = 0) { return Math.sin(t * f + p) * a }

function updateIdle (t, dt) {
  if (!vrm?.humanoid) return

  const get = name => vrm.humanoid.getNormalizedBoneNode(name)

  // 呼吸：多频叠加，带轻微随机感
  const breath = sw(t, 0.78, 0.013) + sw(t, 1.56, 0.003, 0.4) + sw(t, 0.31, 0.005, 1.2)

  // 极慢的身体整体漂移（0.1 Hz 级别），模拟站立时的微小重心调整
  const bodyLeanZ = sw(t, 0.13, 0.010, 0.0) + sw(t, 0.07, 0.005, 2.1)
  const bodyLeanX = sw(t, 0.11, 0.007, 1.0)

  // 脊椎
  const spine = get('spine')
  if (spine) {
    spine.rotation.x = pose.spineX + breath + bodyLeanX
    spine.rotation.z = pose.spineZ + sw(t, 0.22, 0.006, 0.8) + bodyLeanZ
  }
  const chest = get('chest')
  if (chest) chest.rotation.x = pose.chestX + breath * 0.55

  // 头部：侧倾 + 偶发 look-around + 鼠标跟随
  const head = get('head')
  if (head) {
    head.rotation.z = sw(t, 0.32, 0.013, 0.5) + sw(t, 0.85, 0.004)
    head.rotation.y = ism.headCurY + gaze.headY
    head.rotation.x = gaze.headX
  }

  // 眼球：直接操作骨骼跟随鼠标
  const lEye = get('leftEye')
  const rEye = get('rightEye')
  if (lEye) { lEye.rotation.y = gaze.eyeY; lEye.rotation.x = gaze.eyeX }
  if (rEye) { rEye.rotation.y = gaze.eyeY; rEye.rotation.x = gaze.eyeX }

  // 手臂：pose 基准 + 随呼吸微浮（很小，不突兀）
  const breathArmZ = breath * 0.35
  const lArm = get('leftUpperArm')
  if (lArm) { lArm.rotation.x = pose.lArmX; lArm.rotation.y = pose.lArmY; lArm.rotation.z = pose.lArmZ + breathArmZ }
  const rArm = get('rightUpperArm')
  if (rArm) { rArm.rotation.x = pose.rArmX; rArm.rotation.y = pose.rArmY; rArm.rotation.z = pose.rArmZ - breathArmZ }

  // 前臂：轻微随呼吸弯曲
  const lFore = get('leftLowerArm')
  if (lFore) lFore.rotation.x = pose.lForeX + breath * 0.08
  const rFore = get('rightLowerArm')
  if (rFore) rFore.rotation.x = pose.rForeX + breath * 0.08

  // 髋部：重心左右移 + 随呼吸微微起伏
  const hips = get('hips')
  if (hips) {
    const weightShift = sw(t, 0.17, 0.009, 0.3) + sw(t, 0.08, 0.004, 1.8)
    hips.rotation.z   = weightShift
    hips.position.x   = weightShift * 0.025
    hips.position.y   = sw(t, 0.78, 0.003) + sw(t, 1.56, 0.001, 0.4)
  }
}

// ── 渲染循环 ─────────────────────────────────────────────────
function tick () {
  requestAnimationFrame(tick)
  const dt = clock.getDelta()
  const t  = clock.getElapsedTime()

  if (vrm) {
    // 平滑插值视线：眼球快（8×/s），头部慢（2.5×/s）
    const lerp = (cur, tgt, spd) => cur + (tgt - cur) * Math.min(dt * spd, 1)
    gaze.eyeY  = lerp(gaze.eyeY,  _gazeTgt.eyeY,  8.0)
    gaze.eyeX  = lerp(gaze.eyeX,  _gazeTgt.eyeX,  8.0)
    gaze.headY = lerp(gaze.headY, _gazeTgt.headY, 2.5)
    gaze.headX = lerp(gaze.headX, _gazeTgt.headX, 2.5)
    updateISM(dt)
    updateIdle(t, dt)
    applyPresetBlend(dt)
    updateExpressions(dt)
    updateBlink(dt)
    if (exprTimer !== Infinity && exprTimer > 0 && (exprTimer -= dt) <= 0) clearExpr()
    vrm.update(dt)
  }

  renderer.render(scene, camera)
}
tick()

// ── 窗口拖动 & 点击 ───────────────────────────────────────────
let dragOrigin = null, moved = false

canvas.addEventListener('mousedown', e => {
  if (e.button !== 0) return
  dragOrigin = { x: e.clientX, y: e.clientY, sx: e.screenX, sy: e.screenY }; moved = false
})
canvas.addEventListener('mousemove', e => {
  if (!dragOrigin) return
  const dx = e.screenX - dragOrigin.sx, dy = e.screenY - dragOrigin.sy
  if (!moved && (Math.abs(dx) > 4 || Math.abs(dy) > 4)) moved = true
  if (moved) {
    window.yukiAPI.moveWindow(dx, dy)
    dragOrigin.sx = e.screenX; dragOrigin.sy = e.screenY
    dragOrigin.x  = e.clientX; dragOrigin.y  = e.clientY
  }
})
canvas.addEventListener('mouseup', e => {
  if (e.button === 0 && !moved && vrm) applyExpr(CLICK_CYCLE[clickIdx++ % CLICK_CYCLE.length], 0.9, 2.5)
  dragOrigin = null; moved = false
})
canvas.addEventListener('contextmenu', e => { e.preventDefault(); window.yukiAPI.showContextMenu() })

// ── Pose 面板 ─────────────────────────────────────────────────
const panel = document.getElementById('pose-panel')
let panelOpen = false

// 面板里的滑块配置
const SLIDERS = [
  { section: '相机' },
  { key: 'camZ',  label: '距离',   min: 1,    max: 10,  step: 0.05, onApply: updateCamera },
  { key: 'camY',  label: '高度',   min: 0,    max: 2.5, step: 0.02, onApply: updateCamera },
  { key: 'lookY', label: '视点Y',  min: 0,    max: 2.5, step: 0.02, onApply: updateCamera },
  { key: 'fov',   label: '视野角', min: 10,   max: 60,  step: 0.5,  onApply: updateCamera },
  { section: '躯干' },
  { key: 'spineX', label: '脊椎X', min: -0.5, max: 0.5, step: 0.01 },
  { key: 'spineZ', label: '脊椎Z', min: -0.5, max: 0.5, step: 0.01 },
  { key: 'chestX', label: '胸X',   min: -0.5, max: 0.5, step: 0.01 },
  { section: '左臂' },
  { key: 'lArmX', label: 'X', min: -2, max: 2, step: 0.02 },
  { key: 'lArmY', label: 'Y', min: -2, max: 2, step: 0.02 },
  { key: 'lArmZ', label: 'Z', min: -2, max: 2, step: 0.02 },
  { key: 'lForeX', label: '前臂X', min: -0.5, max: 2.5, step: 0.02 },
  { section: '右臂' },
  { key: 'rArmX', label: 'X', min: -2, max: 2, step: 0.02 },
  { key: 'rArmY', label: 'Y', min: -2, max: 2, step: 0.02 },
  { key: 'rArmZ', label: 'Z', min: -2, max: 2, step: 0.02 },
  { key: 'rForeX', label: '前臂X', min: -0.5, max: 2.5, step: 0.02 },
]

// 记住每个 key 对应的 span 元素（用于 syncPanelValues）
const valSpans = {}

function buildPanel () {
  panel.innerHTML = ''

  const title = document.createElement('div')
  title.className = 'panel-title'
  title.innerHTML = 'Pose Editor <kbd>P</kbd>'
  panel.appendChild(title)

  for (const s of SLIDERS) {
    if (s.section !== undefined) {
      const lbl = document.createElement('div')
      lbl.className = 'section-label'
      lbl.textContent = s.section
      panel.appendChild(lbl)
      continue
    }

    const row = document.createElement('div')
    row.className = 'slider-row'

    const lbl = document.createElement('label')
    const valSpan = document.createElement('span')
    valSpan.className = 'val'
    valSpan.textContent = pose[s.key].toFixed(2)
    valSpans[s.key] = valSpan
    lbl.append(s.label, valSpan)

    const input = document.createElement('input')
    input.type = 'range'
    input.min = s.min; input.max = s.max; input.step = s.step
    input.value = pose[s.key]
    input.addEventListener('input', () => {
      pose[s.key] = parseFloat(input.value)
      valSpan.textContent = pose[s.key].toFixed(2)
      if (s.onApply) s.onApply()
    })

    row.append(lbl, input)
    panel.appendChild(row)
  }

  const exportBtn = document.createElement('button')
  exportBtn.className = 'panel-btn'
  exportBtn.textContent = '📋 复制 JSON'
  exportBtn.addEventListener('click', () => {
    const out = JSON.stringify(pose, null, 2)
    navigator.clipboard.writeText(out).then(() => {
      exportBtn.textContent = '✓ 已复制'
      setTimeout(() => { exportBtn.textContent = '📋 复制 JSON' }, 1500)
    })
  })
  panel.appendChild(exportBtn)
}

function syncPanelValues () {
  // VRM 加载完成后用自动适配的相机值更新滑块
  for (const [key, span] of Object.entries(valSpans)) {
    if (span) span.textContent = pose[key].toFixed(2)
    const input = panel.querySelector(`input[data-key="${key}"]`)
    if (input) input.value = pose[key]
  }
  // 直接重建面板以同步滑块位置
  if (panelOpen) buildPanel()
}

function togglePanel () {
  panelOpen = !panelOpen
  if (panelOpen) {
    buildPanel()
    panel.classList.remove('hidden')
    window.yukiAPI.setWindowWidth(CANVAS_W + 200)
  } else {
    panel.classList.add('hidden')
    window.yukiAPI.setWindowWidth(CANVAS_W)
  }
}

document.addEventListener('keydown', e => {
  if (e.key === 'p' || e.key === 'P') togglePanel()
})

// ── Resize ────────────────────────────────────────────────────
window.addEventListener('resize', () => {
  renderer.setSize(CANVAS_W, window.innerHeight)
  camera.aspect = CANVAS_W / window.innerHeight
  camera.updateProjectionMatrix()
})
