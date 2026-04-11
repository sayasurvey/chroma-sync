import React, { useState } from 'react'
import { ConversionOptionsPanel } from '@/components/ConversionOptions'
import { FileUpload } from '@/components/FileUpload'
import { ProgressBar } from '@/components/ProgressBar'
import { ResultPreview } from '@/components/ResultPreview'
import { useConversion } from '@/hooks/useConversion'
import type { ConversionOptions } from '@/types/conversion'
import styles from './App.module.css'

const DEFAULT_OPTIONS: ConversionOptions = {
  quality: 85,
  maxDeltaE: 2.0,
  useLlm: false,
}

export default function App() {
  const [options, setOptions] = useState<ConversionOptions>(DEFAULT_OPTIONS)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const { state, jobId, progress, result, error, convert, reset } = useConversion()

  const handleFileSelect = (file: File) => {
    setSelectedFile(file)
  }

  const handleConvert = () => {
    if (selectedFile) {
      convert(selectedFile, options)
    }
  }

  const handleReset = () => {
    reset()
    setSelectedFile(null)
  }

  const isProcessing = state === 'uploading' || state === 'converting'

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <h1 className={styles.logo}>chroma-sync</h1>
          <p className={styles.tagline}>AI / PSD → JPEG 色味保持変換</p>
        </div>
      </header>

      <main className={styles.main}>
        {state !== 'completed' && (
          <div className={styles.grid}>
            {/* 左側: アップロードと変換 */}
            <div className={styles.leftColumn}>
              <section className={styles.section}>
                <h2 className={styles.sectionTitle}>ファイルを選択</h2>
                <FileUpload
                  onFileSelect={handleFileSelect}
                  disabled={isProcessing}
                />

                {selectedFile && (
                  <div className={styles.selectedFile}>
                    <span className={styles.fileIcon}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                      </svg>
                    </span>
                    <span className={styles.fileName}>{selectedFile.name}</span>
                    <span className={styles.fileSize}>
                      ({(selectedFile.size / 1024 / 1024).toFixed(1)} MB)
                    </span>
                  </div>
                )}
              </section>

              {/* 変換ボタン */}
              {selectedFile && !isProcessing && (
                <button
                  onClick={handleConvert}
                  className={styles.convertButton}
                >
                  変換を開始
                </button>
              )}

              {/* 進捗バー */}
              {isProcessing && progress && (
                <section className={styles.section}>
                  <ProgressBar progress={progress} />
                </section>
              )}

              {/* エラー表示 */}
              {state === 'failed' && error && (
                <div className={styles.errorBox}>
                  <p className={styles.errorText}>{error}</p>
                  <button onClick={handleReset} className={styles.retryButton}>
                    やり直す
                  </button>
                </div>
              )}
            </div>

            {/* 右側: オプション設定 */}
            <div className={styles.rightColumn}>
              <section className={styles.section}>
                <ConversionOptionsPanel
                  options={options}
                  onChange={setOptions}
                  disabled={isProcessing}
                />
              </section>
            </div>
          </div>
        )}

        {/* 変換完了: 結果表示 */}
        {state === 'completed' && result && jobId && selectedFile && (
          <ResultPreview
            jobId={jobId}
            result={result}
            originalFileName={selectedFile.name}
            onReset={handleReset}
          />
        )}
      </main>

      <footer className={styles.footer}>
        <p>chroma-sync &copy; 2024 — AI/PSD to JPEG with color fidelity</p>
      </footer>
    </div>
  )
}
