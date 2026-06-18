const { app, BrowserWindow, ipcMain, Menu, screen } = require('electron')
const path = require('path')
const fs   = require('fs')

const BOT_ROOT  = path.join(__dirname, '..')
const LT_STATE  = path.join(BOT_ROOT, 'data', 'lt_state.json')
const VRM_PATH     = path.join(BOT_ROOT, 'Yuki.vrm')
const PRESETS_PATH = path.join(BOT_ROOT, 'data', 'presets.json')

let win = null
let editorWin = null

function openEditor () {
  if (editorWin && !editorWin.isDestroyed()) { editorWin.focus(); return }
  editorWin = new BrowserWindow({
    width: 1280, height: 820,
    title: 'Yuki — Pose Editor',
    webPreferences: {
      preload: path.join(__dirname, 'preload-editor.js'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: false,
    },
  })
  editorWin.loadFile('renderer/editor.html')
  editorWin.on('closed', () => { editorWin = null })
}

function createWindow () {
  win = new BrowserWindow({
    width:  380,
    height: 640,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: false,
    resizable: false,
    hasShadow: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: false,   // allow file:// fetch for local VRM
    },
  })

  win.loadFile('renderer/index.html')

  // Ctrl+Shift+I 打开 DevTools
  const { globalShortcut } = require('electron')
  globalShortcut.register('CommandOrControl+Shift+I', () => {
    if (win && !win.isDestroyed()) win.webContents.toggleDevTools()
  })
  globalShortcut.register('CommandOrControl+Shift+E', openEditor)
}

app.whenReady().then(() => {
  createWindow()

  // ── IPC handlers ────────────────────────────────────────────
  ipcMain.handle('get-vrm-path', () => VRM_PATH)
  ipcMain.handle('open-editor', openEditor)
  ipcMain.handle('save-presets', (_, data) => {
    fs.writeFileSync(PRESETS_PATH, JSON.stringify(data, null, 2), 'utf8')
  })
  ipcMain.handle('load-presets', () => {
    try { return JSON.parse(fs.readFileSync(PRESETS_PATH, 'utf8')) }
    catch { return {} }
  })

  ipcMain.on('move-window', (_, dx, dy) => {
    if (!win || win.isDestroyed()) return
    const [x, y] = win.getPosition()
    win.setPosition(x + dx, y + dy)
  })

  ipcMain.on('set-window-width', (_, width) => {
    if (!win || win.isDestroyed()) return
    const [, h] = win.getSize()
    win.setSize(width, h)
    win.setResizable(false)
  })

  ipcMain.on('show-context-menu', () => {
    if (!win || win.isDestroyed()) return

    // 动态读取预设列表
    let presetSubmenu = []
    try {
      const saved = JSON.parse(fs.readFileSync(PRESETS_PATH, 'utf8'))
      const names = Object.keys(saved)
      if (names.length) {
        presetSubmenu = names.map(name => ({
          label: name,
          click: () => win.webContents.send('apply-preset', saved[name]),
        }))
        presetSubmenu.push({ type: 'separator' })
        presetSubmenu.push({ label: '清除预设', click: () => win.webContents.send('apply-preset', null) })
      }
    } catch { /* presets.json 不存在或为空 */ }

    const template = [
      {
        label: '置顶',
        type: 'checkbox',
        checked: win.isAlwaysOnTop(),
        click: () => win.setAlwaysOnTop(!win.isAlwaysOnTop()),
      },
      { type: 'separator' },
    ]
    if (presetSubmenu.length) {
      template.push({ label: '预设', submenu: presetSubmenu })
      template.push({ type: 'separator' })
    }
    template.push({ label: 'Pose Editor  ⌘⇧E', click: openEditor })
    template.push({ type: 'separator' })
    template.push({ label: '退出', click: () => app.quit() })

    Menu.buildFromTemplate(template).popup({ window: win })
  })

  // ── Global cursor tracking @ ~30fps → renderer 做全屏视线跟随
  setInterval(() => {
    if (!win || win.isDestroyed()) return
    const pt = screen.getCursorScreenPoint()
    const [wx, wy] = win.getPosition()
    const [ww, wh] = win.getSize()
    win.webContents.send('cursor-pos', pt.x, pt.y, wx, wy, ww, wh)
  }, 33)

  // ── Mood polling：15–30 分钟随机间隔，每次触发后重新调度
  ;(function scheduleMoodPoll () {
    const delay = (15 + Math.random() * 15) * 60_000
    setTimeout(() => {
      try {
        const state = JSON.parse(fs.readFileSync(LT_STATE, 'utf8'))
        const mood = state.last_mood
        if (mood && win && !win.isDestroyed()) win.webContents.send('lt-mood', mood)
      } catch { /* lt_state not ready */ }
      scheduleMoodPoll()
    }, delay)
  })()
})

app.on('window-all-closed', () => app.quit())
