const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('editorAPI', {
  getVRMPath:   () => ipcRenderer.invoke('get-vrm-path'),
  savePresets:  (data) => ipcRenderer.invoke('save-presets', data),
  loadPresets:  () => ipcRenderer.invoke('load-presets'),
})
