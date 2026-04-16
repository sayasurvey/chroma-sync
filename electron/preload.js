'use strict'

// コンテキスト分離済み環境でのプリロードスクリプト。
// レンダラープロセスはnodeIntegration=falseのため、
// 必要に応じてcontextBridge経由でAPIを公開する。

const { contextBridge } = require('electron')

// バックエンドAPIのベースURL（レンダラーから参照可能にする）
contextBridge.exposeInMainWorld('__CHROMA_SYNC__', {
  apiBaseUrl: 'http://127.0.0.1:8000',
})
