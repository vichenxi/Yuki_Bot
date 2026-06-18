const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('yukiAPI', {
  getVRMPath:      ()         => ipcRenderer.invoke('get-vrm-path'),
  moveWindow:      (dx, dy)   => ipcRenderer.send('move-window', dx, dy),
  setWindowWidth:  (w)        => ipcRenderer.send('set-window-width', w),
  showContextMenu: ()         => ipcRenderer.send('show-context-menu'),
  onMood:          (cb)       => ipcRenderer.on('lt-mood', (_, mood) => cb(mood)),
  onCursor:        (cb)       => ipcRenderer.on('cursor-pos', (_, cx, cy, wx, wy, ww, wh) => cb(cx, cy, wx, wy, ww, wh)),
  onPresetApply:   (cb)       => ipcRenderer.on('apply-preset', (_, preset) => cb(preset)),
})
