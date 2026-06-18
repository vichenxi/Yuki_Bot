import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { VRMLoaderPlugin, VRMUtils, VRMExpression, VRMExpressionMorphTargetBind } from '@pixiv/three-vrm'

// ── Part / bone definitions ───────────────────────────────────
const PARTS = {
  spine: { label: '躯干', joints: [
    { name: 'hips',        label: 'Hips'        },
    { name: 'spine',       label: 'Spine'       },
    { name: 'chest',       label: 'Chest'       },
    { name: 'upperChest',  label: 'Upper Chest' },
  ]},
  head: { label: '头颈', joints: [
    { name: 'neck', label: 'Neck' },
    { name: 'head', label: 'Head' },
    { name: 'jaw',  label: 'Jaw'  },
  ]},
  larm: { label: '左臂', joints: [
    { name: 'leftShoulder', label: 'Shoulder'  },
    { name: 'leftUpperArm', label: 'Upper Arm' },
    { name: 'leftLowerArm', label: 'Lower Arm' },
  ]},
  rarm: { label: '右臂', joints: [
    { name: 'rightShoulder', label: 'Shoulder'  },
    { name: 'rightUpperArm', label: 'Upper Arm' },
    { name: 'rightLowerArm', label: 'Lower Arm' },
  ]},
  lhand: { label: '左手', side: 'left',  fingers: true, joints: [
    { name: 'leftHand', label: 'Wrist' },
  ]},
  rhand: { label: '右手', side: 'right', fingers: true, joints: [
    { name: 'rightHand', label: 'Wrist' },
  ]},
  lleg: { label: '左腿', joints: [
    { name: 'leftUpperLeg', label: 'Upper Leg' },
    { name: 'leftLowerLeg', label: 'Lower Leg' },
    { name: 'leftFoot',     label: 'Foot'      },
    { name: 'leftToes',     label: 'Toes'      },
  ]},
  rleg: { label: '右腿', joints: [
    { name: 'rightUpperLeg', label: 'Upper Leg' },
    { name: 'rightLowerLeg', label: 'Lower Leg' },
    { name: 'rightFoot',     label: 'Foot'      },
    { name: 'rightToes',     label: 'Toes'      },
  ]},
}

const FINGER_DEF = [
  { key: 'thumb',  label: 'Thumb',  bones: { left: ['leftThumbMetacarpal','leftThumbProximal','leftThumbDistal'],                                    right: ['rightThumbMetacarpal','rightThumbProximal','rightThumbDistal'] }},
  { key: 'index',  label: 'Index',  bones: { left: ['leftIndexProximal','leftIndexIntermediate','leftIndexDistal'],         right: ['rightIndexProximal','rightIndexIntermediate','rightIndexDistal'] }},
  { key: 'middle', label: 'Middle', bones: { left: ['leftMiddleProximal','leftMiddleIntermediate','leftMiddleDistal'],       right: ['rightMiddleProximal','rightMiddleIntermediate','rightMiddleDistal'] }},
  { key: 'ring',   label: 'Ring',   bones: { left: ['leftRingProximal','leftRingIntermediate','leftRingDistal'],             right: ['rightRingProximal','rightRingIntermediate','rightRingDistal'] }},
  { key: 'little', label: 'Little', bones: { left: ['leftLittleProximal','leftLittleIntermediate','leftLittleDistal'],       right: ['rightLittleProximal','rightLittleIntermediate','rightLittleDistal'] }},
]

// ── State ─────────────────────────────────────────────────────
const boneVals   = {}
const exprVals   = {}
// morphGroups: name → [{mesh, idx}]  (同名 morph 合并跨 mesh)
const morphGroups = new Map()
const morphVals   = {}   // key: morphName → 0..1
let presets    = {}
let vrm        = null
let activePart = 'spine'
let activeTab  = 'bones'

// initialise all boneVals
for (const part of Object.values(PARTS)) {
  for (const j of part.joints) boneVals[j.name] = { x: 0, y: 0, z: 0 }
  if (part.fingers) {
    for (const fd of FINGER_DEF) {
      for (const name of fd.bones[part.side]) boneVals[name] = { x: 0, y: 0, z: 0 }
    }
  }
}

// ── Three.js ──────────────────────────────────────────────────
const canvas   = document.getElementById('canvas')
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true })
renderer.setPixelRatio(window.devicePixelRatio)
renderer.outputColorSpace = THREE.SRGBColorSpace

const scene  = new THREE.Scene()
scene.background = new THREE.Color(0x0d0d14)

const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 100)
camera.position.set(0, 1.2, 4)

const controls = new OrbitControls(camera, canvas)
controls.target.set(0, 1.0, 0)
controls.enableDamping = true
controls.dampingFactor = 0.08

scene.add(new THREE.AmbientLight(0xffffff, 1.2))
const sun = new THREE.DirectionalLight(0xffffff, 1.4)
sun.position.set(1.5, 3, 2); scene.add(sun)
const fill = new THREE.DirectionalLight(0xeef4ff, 0.5)
fill.position.set(-2, 1, -1); scene.add(fill)
scene.add(new THREE.GridHelper(4, 20, 0x1c1c2c, 0x151525))

new ResizeObserver(() => {
  const w = canvas.clientWidth, h = canvas.clientHeight
  if (!w || !h) return
  renderer.setSize(w, h, false)
  camera.aspect = w / h
  camera.updateProjectionMatrix()
}).observe(canvas)

const clock = new THREE.Clock()
;(function tick () {
  requestAnimationFrame(tick)
  controls.update()
  if (vrm) { applyMorphs(); vrm.update(clock.getDelta()) }
  renderer.render(scene, camera)
})()

// ── VRM load ──────────────────────────────────────────────────
const loader = new GLTFLoader()
loader.register(p => new VRMLoaderPlugin(p))

async function loadVRM () {
  const path = await window.editorAPI.getVRMPath()
  const gltf = await loader.loadAsync('file:///' + path.replace(/\\/g, '/'))
  vrm = gltf.userData.vrm
  if (vrm.meta?.metaVersion === '0' || !vrm.meta?.metaVersion) VRMUtils.rotateVRM0(vrm)

  const box = new THREE.Box3().setFromObject(vrm.scene)
  vrm.scene.position.x -= (box.max.x + box.min.x) / 2
  vrm.scene.position.y -= box.min.y
  const h = box.max.y - box.min.y
  controls.target.set(0, h * 0.5, 0)
  camera.position.set(0, h * 0.5, h * 2.3)
  controls.update()
  scene.add(vrm.scene)

  if (vrm.expressionManager)
    for (const name of Object.keys(vrm.expressionManager.expressionMap))
      exprVals[name] = 0

  // 跨 mesh 聚合同名 morph
  vrm.scene.traverse(obj => {
    if (!obj.isMesh || !obj.morphTargetDictionary) return
    for (const [name, idx] of Object.entries(obj.morphTargetDictionary)) {
      if (!morphGroups.has(name)) morphGroups.set(name, [])
      morphGroups.get(name).push({ mesh: obj, idx })
    }
  })

  // 每个唯一 morph 名注册一个 expression，绑定所有相关 mesh
  if (vrm.expressionManager) {
    for (const [name, binds] of morphGroups) {
      const expr = new VRMExpression(`__m:${name}`)
      for (const { mesh, idx } of binds)
        expr.addBind(new VRMExpressionMorphTargetBind({ primitives: [mesh], index: idx, weight: 1.0 }))
      vrm.expressionManager.registerExpression(expr)
      morphVals[name] = 0
    }
  }

  renderPropPanel()
  pushHistory()
}
loadVRM().catch(e => console.error('[editor]', e))

// ── Apply to model ────────────────────────────────────────────
function applyBones () {
  if (!vrm?.humanoid) return
  for (const [name, r] of Object.entries(boneVals)) {
    const bone = vrm.humanoid.getNormalizedBoneNode(name)
    if (bone) { bone.rotation.x = r.x; bone.rotation.y = r.y; bone.rotation.z = r.z }
  }
}

function applyExpressions () {
  if (!vrm?.expressionManager) return
  for (const [name, w] of Object.entries(exprVals)) vrm.expressionManager.setValue(name, w)
  vrm.expressionManager.update()
}

function applyMorphs () {
  if (!vrm?.expressionManager) return
  for (const name of morphGroups.keys())
    vrm.expressionManager.setValue(`__m:${name}`, morphVals[name] ?? 0)
}

// ── History ───────────────────────────────────────────────────
const hist = []
let histIdx = -1

function cloneState () {
  const bones = {}
  for (const [k, v] of Object.entries(boneVals)) bones[k] = { ...v }
  return { bones, exprs: { ...exprVals }, morphs: { ...morphVals } }
}

function pushHistory () {
  hist.splice(histIdx + 1)
  hist.push(cloneState())
  if (hist.length > 60) hist.shift(); else histIdx++
  refreshHistBtns()
}

function restoreState (s) {
  for (const [k, v] of Object.entries(s.bones)) boneVals[k] = { ...v }
  for (const [k, v] of Object.entries(s.exprs))  exprVals[k] = v
  if (s.morphs) for (const [k, v] of Object.entries(s.morphs)) if (k in morphVals) morphVals[k] = v
  applyBones(); applyExpressions(); syncSliders()
}

function undo () { if (histIdx > 0)                    restoreState(hist[--histIdx]); refreshHistBtns() }
function redo () { if (histIdx < hist.length - 1)      restoreState(hist[++histIdx]); refreshHistBtns() }

function refreshHistBtns () {
  document.getElementById('btn-undo').disabled = histIdx <= 0
  document.getElementById('btn-redo').disabled = histIdx >= hist.length - 1
}

document.addEventListener('keydown', e => {
  const mod = e.ctrlKey || e.metaKey
  if (mod && e.key === 'z' && !e.shiftKey) { e.preventDefault(); undo() }
  if (mod && e.key === 'z' &&  e.shiftKey) { e.preventDefault(); redo() }
  if (mod && e.key === 'y')                { e.preventDefault(); redo() }
})

// ── Sync sliders after state restore ─────────────────────────
function syncSliders () {
  document.querySelectorAll('input[data-bone]').forEach(s => {
    const v = boneVals[s.dataset.bone]?.[s.dataset.axis] ?? 0
    s.value = String(v)
    const ni = document.querySelector(`[data-bv="${s.dataset.bone}|${s.dataset.axis}"]`)
    if (ni) ni.value = v.toFixed(2)
  })
  document.querySelectorAll('input[data-expr]').forEach(s => {
    const v = exprVals[s.dataset.expr] ?? 0
    s.value = String(v)
    const ni = document.querySelector(`[data-ev="${s.dataset.expr}"]`)
    if (ni) ni.value = v.toFixed(2)
  })
  document.querySelectorAll('input[data-curlbones]').forEach(s => {
    const names = s.dataset.curlbones.split(',')
    const avg = names.reduce((a, n) => a + (boneVals[n]?.x ?? 0), 0) / names.length
    s.value = String(avg)
    const ni = s.parentElement?.querySelector('[data-curlval]')
    if (ni) ni.value = avg.toFixed(2)
  })
  document.querySelectorAll('input[data-mk]').forEach(s => {
    const v = morphVals[s.dataset.mk] ?? 0
    s.value = String(v)
    const ni = s.parentElement?.querySelector('[data-mv]')
    if (ni) ni.value = v.toFixed(2)
  })
  // (data-mv inputs are inside the same row — synced above via parentElement)
}

// ── Render prop panel ─────────────────────────────────────────
function renderPropPanel () {
  const panel = document.getElementById('prop-panel')
  panel.innerHTML = ''
  if      (activeTab === 'bones')   renderBonesTab(panel)
  else if (activeTab === 'expr')    renderExprTab(panel)
  else if (activeTab === 'morphs')  renderMorphsTab(panel)
  else if (activeTab === 'presets') renderPresetsTab(panel)
}

// ── Bones tab ─────────────────────────────────────────────────
function renderBonesTab (panel) {
  const part = PARTS[activePart]
  if (!part) return

  panel.appendChild(E('div', 'part-hdr', part.label.toUpperCase()))

  for (const { name, label } of part.joints) {
    if (!boneExists(name)) continue
    panel.appendChild(makeJointSection(name, label))
  }

  if (part.fingers) {
    panel.appendChild(E('div', 'fingers-divider', 'Fingers'))
    for (const fd of FINGER_DEF) {
      const boneNames = fd.bones[part.side]
      if (!boneExists(boneNames[0])) continue
      panel.appendChild(makeFingerSection(fd.label, boneNames))
    }
  }
}

function boneExists (name) {
  return !!vrm?.humanoid?.getNormalizedBoneNode(name)
}

function makeJointSection (boneName, label) {
  const sec = E('div', 'joint-sec')
  const hdr = E('div', 'joint-hdr')
  const lbl = E('span', 'joint-lbl', label)
  const rst = E('button', 'joint-rst', '↺')
  rst.title = 'Reset bone'
  rst.addEventListener('click', () => {
    boneVals[boneName] = { x: 0, y: 0, z: 0 }
    applyBones(); syncSliders(); pushHistory()
  })
  hdr.append(lbl, rst)
  sec.appendChild(hdr)
  for (const axis of ['x', 'y', 'z']) sec.appendChild(makeAxisRow(boneName, axis))
  return sec
}

function makeAxisRow (boneName, axis) {
  const row = E('div', 'axis-row')
  const lbl = E('span', 'ax-lbl', axis.toUpperCase())

  const slider = document.createElement('input')
  slider.type  = 'range'
  slider.min   = (-Math.PI).toFixed(4)
  slider.max   = ( Math.PI).toFixed(4)
  slider.step  = '0.005'
  slider.value = String(boneVals[boneName]?.[axis] ?? 0)
  slider.dataset.bone = boneName
  slider.dataset.axis = axis

  const numIn = makeNumInput(-Math.PI, Math.PI, boneVals[boneName]?.[axis] ?? 0)
  numIn.dataset.bv = `${boneName}|${axis}`

  slider.addEventListener('input', () => {
    const v = parseFloat(slider.value)
    if (!boneVals[boneName]) boneVals[boneName] = { x: 0, y: 0, z: 0 }
    boneVals[boneName][axis] = v
    numIn.value = v.toFixed(2)
    applyBones()
  })
  slider.addEventListener('change', pushHistory)

  numIn.addEventListener('input', () => {
    const v = clampNum(parseFloat(numIn.value), -Math.PI, Math.PI)
    if (isNaN(v)) return
    if (!boneVals[boneName]) boneVals[boneName] = { x: 0, y: 0, z: 0 }
    boneVals[boneName][axis] = v
    slider.value = String(v)
    applyBones()
  })
  numIn.addEventListener('change', () => {
    const v = clampNum(parseFloat(numIn.value), -Math.PI, Math.PI)
    numIn.value = isNaN(v) ? (boneVals[boneName]?.[axis] ?? 0).toFixed(2) : v.toFixed(2)
    pushHistory()
  })

  row.append(lbl, slider, numIn)
  return row
}

function makeFingerSection (fingerLabel, boneNames) {
  const sec = E('div', 'finger-sec')
  const hdr = E('div', 'finger-hdr')

  const toggle = E('button', 'finger-toggle', '▶')
  const lbl    = E('span', 'finger-lbl', fingerLabel)

  // Master curl (controls X across all 3 joints)
  const curlWrap   = E('div', 'curl-wrap')
  const curlSlider = document.createElement('input')
  curlSlider.type  = 'range'
  curlSlider.min   = '-1.6'
  curlSlider.max   = '0.4'
  curlSlider.step  = '0.01'
  const avgX = boneNames.reduce((a, n) => a + (boneVals[n]?.x ?? 0), 0) / boneNames.length
  curlSlider.value = String(avgX)
  curlSlider.dataset.curlbones = boneNames.join(',')

  const curlNum = makeNumInput(-1.6, 0.4, avgX, 'var(--green)')
  curlNum.dataset.curlval = '1'

  curlSlider.addEventListener('input', () => {
    const v = parseFloat(curlSlider.value)
    for (const name of boneNames) {
      if (!boneVals[name]) boneVals[name] = { x: 0, y: 0, z: 0 }
      boneVals[name].x = v
    }
    curlNum.value = v.toFixed(2); applyBones()
  })
  curlSlider.addEventListener('change', pushHistory)
  curlNum.addEventListener('input', () => {
    const v = clampNum(parseFloat(curlNum.value), -1.6, 0.4)
    if (isNaN(v)) return
    for (const name of boneNames) {
      if (!boneVals[name]) boneVals[name] = { x: 0, y: 0, z: 0 }
      boneVals[name].x = v
    }
    curlSlider.value = String(v); applyBones()
  })
  curlNum.addEventListener('change', () => {
    const v = clampNum(parseFloat(curlNum.value), -1.6, 0.4)
    curlNum.value = isNaN(v) ? avgX.toFixed(2) : v.toFixed(2)
    pushHistory()
  })
  curlWrap.append(curlSlider, curlNum)

  hdr.append(toggle, lbl, curlWrap)
  sec.appendChild(hdr)

  // Expandable detail (all 3 joints × all 3 axes)
  const detail = E('div', 'finger-detail hidden')
  const subLabels = ['Prox', 'Mid', 'Dist']
  boneNames.forEach((name, i) => {
    if (!boneExists(name)) return
    detail.appendChild(makeJointSection(name, subLabels[i] ?? name))
  })
  toggle.addEventListener('click', () => {
    const nowHidden = detail.classList.toggle('hidden')
    toggle.textContent = nowHidden ? '▶' : '▼'
  })

  sec.append(detail)
  return sec
}

// ── Expression tab ────────────────────────────────────────────
function renderExprTab (panel) {
  panel.appendChild(E('div', 'part-hdr', 'EXPRESSIONS'))
  if (!vrm?.expressionManager) {
    panel.appendChild(E('div', 'empty-hint', 'VRM 未加载'))
    return
  }
  for (const name of Object.keys(vrm.expressionManager.expressionMap)) {
    const row    = E('div', 'axis-row')
    const lbl    = E('span', 'ax-lbl expr-lbl', name)
    const slider = document.createElement('input')
    slider.type  = 'range'; slider.min = '0'; slider.max = '1'; slider.step = '0.01'
    slider.value = String(exprVals[name] ?? 0)
    slider.dataset.expr = name
    slider.classList.add('expr-range')
    const numIn  = makeNumInput(0, 1, exprVals[name] ?? 0, '#9f7aff')
    numIn.dataset.ev = name
    slider.addEventListener('input', () => {
      exprVals[name] = parseFloat(slider.value)
      numIn.value = exprVals[name].toFixed(2)
      applyExpressions()
    })
    slider.addEventListener('change', pushHistory)
    numIn.addEventListener('input', () => {
      const v = clampNum(parseFloat(numIn.value), 0, 1)
      if (isNaN(v)) return
      exprVals[name] = v; slider.value = String(v); applyExpressions()
    })
    numIn.addEventListener('change', () => {
      const v = clampNum(parseFloat(numIn.value), 0, 1)
      numIn.value = isNaN(v) ? (exprVals[name] ?? 0).toFixed(2) : v.toFixed(2)
      pushHistory()
    })
    row.append(lbl, slider, numIn)
    panel.appendChild(row)
  }
}

// ── Morph targets tab ─────────────────────────────────────────
const MORPH_GROUPS = [
  { label: '眉毛 Brow',   test: n => n.includes('BRW') || n.includes('Brow') },
  { label: '眼睛 Eye',    test: n => n.includes('EYE') || n.includes('Eye') || n.includes('HL') },
  { label: '嘴 Mouth',    test: n => n.includes('MTH') || n.includes('Mouth') || n.includes('Lip') },
  { label: '全脸 All',    test: n => n.includes('ALL') || n.includes('All')  },
  { label: '眼白 White',  test: n => n.includes('WH')  },
]

function makeMorphRow (name) {
  const row    = E('div', 'axis-row')
  const lbl    = E('span', 'ax-lbl expr-lbl', name)
  const slider = document.createElement('input')
  slider.type  = 'range'; slider.min = '0'; slider.max = '1'; slider.step = '0.01'
  slider.value = String(morphVals[name] ?? 0)
  slider.dataset.mk = name
  slider.classList.add('expr-range')
  const numIn = makeNumInput(0, 1, morphVals[name] ?? 0, '#9f7aff')
  numIn.dataset.mv = name
  const update = () => { applyMorphs(); vrm?.expressionManager?.update() }
  slider.addEventListener('input', () => {
    morphVals[name] = parseFloat(slider.value)
    numIn.value = morphVals[name].toFixed(2)
    update()
  })
  slider.addEventListener('change', pushHistory)
  numIn.addEventListener('input', () => {
    const v = clampNum(parseFloat(numIn.value), 0, 1)
    if (isNaN(v)) return
    morphVals[name] = v; slider.value = String(v); update()
  })
  numIn.addEventListener('change', () => {
    const v = clampNum(parseFloat(numIn.value), 0, 1)
    numIn.value = isNaN(v) ? (morphVals[name] ?? 0).toFixed(2) : v.toFixed(2)
    pushHistory()
  })
  row.append(lbl, slider, numIn)
  return row
}

function renderMorphsTab (panel) {
  panel.appendChild(E('div', 'part-hdr', 'MORPH TARGETS'))
  if (!morphGroups.size) {
    panel.appendChild(E('div', 'empty-hint', '无 morph target（VRM 未加载或模型无 morph）'))
    return
  }
  const allNames  = [...morphGroups.keys()].sort()
  const assigned  = new Set()

  for (const grp of MORPH_GROUPS) {
    const names = allNames.filter(n => grp.test(n))
    if (!names.length) continue
    panel.appendChild(E('div', 'part-hdr', grp.label))
    names.forEach(n => { assigned.add(n); panel.appendChild(makeMorphRow(n)) })
  }

  const rest = allNames.filter(n => !assigned.has(n))
  if (rest.length) {
    panel.appendChild(E('div', 'part-hdr', '其他 Other'))
    rest.forEach(n => panel.appendChild(makeMorphRow(n)))
  }
}

// ── Presets tab ───────────────────────────────────────────────
function renderPresetsTab (panel) {
  panel.appendChild(E('div', 'part-hdr', 'PRESET LIBRARY'))
  const names = Object.keys(presets)
  if (!names.length) { panel.appendChild(E('div', 'empty-hint', '暂无预设')); return }
  for (const name of names) {
    const item  = E('div', 'preset-item')
    const nm    = E('span', 'preset-name', name)
    const apply = E('button', 'btn-sm blue', '应用')
    const del   = E('button', 'btn-sm red',  '删')
    apply.addEventListener('click', () => applyPreset(name))
    del.addEventListener('click',   () => deletePreset(name))
    item.append(nm, apply, del)
    panel.appendChild(item)
  }
}

// ── Preset strip ──────────────────────────────────────────────
function renderPresetStrip () {
  const chips = document.getElementById('preset-chips')
  chips.innerHTML = ''
  for (const name of Object.keys(presets)) {
    const chip = E('button', 'preset-chip', name)
    chip.addEventListener('click', () => applyPreset(name))
    chips.appendChild(chip)
  }
}

// ── Preset CRUD ───────────────────────────────────────────────
async function saveCurrentPreset () {
  const name = document.getElementById('preset-name-input').value.trim()
  if (!name) return
  const boneData = {}
  for (const [k, v] of Object.entries(boneVals))
    if (v.x || v.y || v.z) boneData[k] = [+v.x.toFixed(3), +v.y.toFixed(3), +v.z.toFixed(3)]
  const exprData = {}
  for (const [k, v] of Object.entries(exprVals))
    if (v > 0.001) exprData[k] = +v.toFixed(3)
  const morphData = {}
  for (const [k, v] of Object.entries(morphVals))
    if (v > 0.001) morphData[k] = +v.toFixed(3)
  presets[name] = { bones: boneData, expressions: exprData, morphs: morphData }
  await window.editorAPI.savePresets(presets)
  document.getElementById('preset-name-input').value = ''
  renderPresetStrip()
  if (activeTab === 'presets') renderPropPanel()
}

function applyPreset (name) {
  const p = presets[name]; if (!p) return
  for (const k of Object.keys(boneVals))  boneVals[k] = { x: 0, y: 0, z: 0 }
  for (const k of Object.keys(exprVals))  exprVals[k] = 0
  for (const k of Object.keys(morphVals))  morphVals[k] = 0
  for (const [k, v] of Object.entries(p.bones ?? {}))
    if (boneVals[k]) boneVals[k] = { x: v[0], y: v[1], z: v[2] }
  for (const [k, v] of Object.entries(p.expressions ?? {}))
    if (k in exprVals) exprVals[k] = v
  for (const [k, v] of Object.entries(p.morphs ?? {}))
    if (k in morphVals) morphVals[k] = v
  applyBones(); applyExpressions(); syncSliders(); pushHistory()
}

async function deletePreset (name) {
  if (!confirm(`删除预设「${name}」？`)) return
  delete presets[name]
  await window.editorAPI.savePresets(presets)
  renderPresetStrip()
  if (activeTab === 'presets') renderPropPanel()
}

async function initPresets () {
  presets = await window.editorAPI.loadPresets()
  renderPresetStrip()
}
initPresets()

// ── Toolbar wiring ────────────────────────────────────────────
document.getElementById('btn-undo').addEventListener('click', undo)
document.getElementById('btn-redo').addEventListener('click', redo)

document.getElementById('btn-reset').addEventListener('click', () => {
  for (const k of Object.keys(boneVals))  boneVals[k] = { x: 0, y: 0, z: 0 }
  for (const k of Object.keys(exprVals))  exprVals[k] = 0
  for (const k of Object.keys(morphVals)) morphVals[k] = 0
  applyBones(); applyExpressions(); syncSliders(); pushHistory()
})

document.getElementById('btn-save-preset').addEventListener('click', saveCurrentPreset)
document.getElementById('preset-name-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') saveCurrentPreset()
})

document.getElementById('btn-copy-json').addEventListener('click', () => {
  navigator.clipboard.writeText(JSON.stringify(cloneState(), null, 2))
  const btn = document.getElementById('btn-copy-json')
  btn.textContent = '✓ Copied'
  setTimeout(() => { btn.textContent = 'Copy JSON' }, 1500)
})

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => btn.addEventListener('click', () => {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'))
  btn.classList.add('active')
  activeTab = btn.dataset.tab
  renderPropPanel()
}))

// Part switching
document.querySelectorAll('.part-btn').forEach(btn => btn.addEventListener('click', () => {
  document.querySelectorAll('.part-btn').forEach(b => b.classList.remove('active'))
  btn.classList.add('active')
  activePart = btn.dataset.part
  if (activeTab === 'bones') renderPropPanel()
}))

// ── Utility ───────────────────────────────────────────────────
function clampNum (v, min, max) { return Math.max(min, Math.min(max, v)) }

function makeNumInput (min, max, initVal, color) {
  const el = document.createElement('input')
  el.type  = 'number'
  el.min   = String(min)
  el.max   = String(max)
  el.step  = '0.01'
  el.value = Number(initVal).toFixed(2)
  el.className = 'num-input'
  if (color) el.style.color = color
  return el
}

function E (tag, cls, text) {
  const e = document.createElement(tag)
  if (cls)  cls.split(' ').forEach(c => c && e.classList.add(c))
  if (text !== undefined) e.textContent = text
  return e
}
