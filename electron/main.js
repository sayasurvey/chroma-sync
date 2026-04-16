'use strict'

const { app, BrowserWindow, shell, dialog } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const http = require('http')

const BACKEND_PORT = 8000
const BACKEND_HOST = '127.0.0.1'
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`

let mainWindow = null
let backendProcess = null

// -----------------------------------------------------------------------
// バックエンドバイナリのパス解決
// -----------------------------------------------------------------------
function getBackendExecutable() {
  if (app.isPackaged) {
    // パッケージ後: resourcesPath/backend/chroma_sync[.exe]
    const ext = process.platform === 'win32' ? '.exe' : ''
    return path.join(process.resourcesPath, 'backend', 'chroma_sync', `chroma_sync${ext}`)
  }
  // 開発時: backend/dist/chroma_sync/chroma_sync
  const ext = process.platform === 'win32' ? '.exe' : ''
  return path.join(__dirname, '..', 'backend', 'dist', 'chroma_sync', `chroma_sync${ext}`)
}

// -----------------------------------------------------------------------
// バックエンドプロセス起動
// -----------------------------------------------------------------------
function startBackend() {
  const execPath = getBackendExecutable()
  console.log(`[backend] 起動: ${execPath}`)

  backendProcess = spawn(execPath, [], {
    env: {
      ...process.env,
      PORT: String(BACKEND_PORT),
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  backendProcess.stdout.on('data', (data) => {
    console.log(`[backend] ${data.toString().trim()}`)
  })
  backendProcess.stderr.on('data', (data) => {
    console.error(`[backend:err] ${data.toString().trim()}`)
  })
  backendProcess.on('error', (err) => {
    console.error('[backend] 起動エラー:', err)
    dialog.showErrorBox(
      'バックエンド起動エラー',
      `変換エンジンの起動に失敗しました。\n${err.message}`
    )
  })
  backendProcess.on('exit', (code, signal) => {
    console.log(`[backend] 終了 code=${code} signal=${signal}`)
    backendProcess = null
  })
}

// -----------------------------------------------------------------------
// バックエンドのヘルスチェック（最大30秒待機）
// -----------------------------------------------------------------------
function waitForBackend(maxAttempts = 30) {
  return new Promise((resolve, reject) => {
    let attempts = 0

    function check() {
      attempts++
      const req = http.get(`${BACKEND_URL}/api/health`, (res) => {
        if (res.statusCode === 200) {
          resolve()
        } else if (attempts >= maxAttempts) {
          reject(new Error(`ヘルスチェック失敗 (status: ${res.statusCode})`))
        } else {
          setTimeout(check, 1000)
        }
      })
      req.on('error', () => {
        if (attempts >= maxAttempts) {
          reject(new Error('バックエンドが起動しませんでした'))
        } else {
          setTimeout(check, 1000)
        }
      })
      req.setTimeout(900, () => req.destroy())
    }

    check()
  })
}

// -----------------------------------------------------------------------
// メインウィンドウ作成
// -----------------------------------------------------------------------
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: 'ChromaSync',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  if (app.isPackaged) {
    // 本番: フロントエンドの静的ファイルをロード
    mainWindow.loadFile(path.join(__dirname, '..', 'frontend', 'dist', 'index.html'))
  } else {
    // 開発: Vite dev server
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  }

  // 外部リンクはデフォルトブラウザで開く
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// -----------------------------------------------------------------------
// アプリライフサイクル
// -----------------------------------------------------------------------
app.whenReady().then(async () => {
  // バックエンドが開発用サーバーとして別途起動されているか確認
  const isDevServer = !app.isPackaged && process.env.SKIP_BACKEND === '1'

  if (!isDevServer) {
    startBackend()
  }

  try {
    console.log('[app] バックエンドの起動を待機中...')
    await waitForBackend()
    console.log('[app] バックエンド準備完了')
  } catch (err) {
    console.error('[app] バックエンド起動タイムアウト:', err.message)
    if (app.isPackaged) {
      dialog.showErrorBox(
        '起動エラー',
        'バックエンドサービスが起動しませんでした。アプリを再起動してください。'
      )
      app.quit()
      return
    }
  }

  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    if (backendProcess) {
      backendProcess.kill('SIGTERM')
    }
    app.quit()
  }
})

app.on('before-quit', () => {
  if (backendProcess) {
    backendProcess.kill('SIGTERM')
  }
})
