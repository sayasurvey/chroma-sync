import { useState } from 'react'
import { ConversionOptionsPanel } from '@/components/ConversionOptions'
import { FileUpload } from '@/components/FileUpload'
import { ProgressBar } from '@/components/ProgressBar'
import { useMultiConversion } from '@/hooks/useMultiConversion'
import type { ConversionOptions, FileConversionItem } from '@/types/conversion'
import { getBatchDownloadUrl, getDownloadUrl, getPreviewUrl } from '@/api/client'
import styles from './App.module.css'

const DEFAULT_OPTIONS: ConversionOptions = {
  quality: 85,
  maxDeltaE: 2.0,
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function StateBadge({ state }: { state: FileConversionItem['state'] }) {
  const map: Record<FileConversionItem['state'], { label: string; cls: string }> = {
    idle: { label: '待機中', cls: styles.badgeIdle },
    uploading: { label: 'アップロード中', cls: styles.badgeUploading },
    converting: { label: '変換中', cls: styles.badgeConverting },
    completed: { label: '完了', cls: styles.badgeCompleted },
    failed: { label: 'エラー', cls: styles.badgeFailed },
  }
  const { label, cls } = map[state]
  return <span className={`${styles.badge} ${cls}`}>{label}</span>
}

function ConversionItemCard({ item }: { item: FileConversionItem }) {
  const isProcessing = item.state === 'uploading' || item.state === 'converting'

  return (
    <div className={`${styles.conversionItem} ${item.state === 'failed' ? styles.conversionItemFailed : ''}`}>
      <div className={styles.conversionItemHeader}>
        <div className={styles.conversionItemNameRow}>
          <svg
            className={styles.fileIconSmall}
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          <span className={styles.conversionItemName}>{item.file.name}</span>
          <span className={styles.conversionItemSize}>{formatBytes(item.file.size)}</span>
        </div>
        <StateBadge state={item.state} />
      </div>

      {isProcessing && (
        <div className={styles.conversionItemBody}>
          <ProgressBar progress={item.progress} />
        </div>
      )}

      {item.state === 'completed' && item.result && item.jobId && (
        <div className={styles.conversionItemBody}>
          <div className={styles.previewRow}>
            <img
              src={getPreviewUrl(item.jobId)}
              alt="変換結果プレビュー"
              className={styles.previewThumb}
            />
            <div className={styles.previewInfo}>
              <div className={styles.resultStats}>
                <span className={styles.resultStat}>
                  {formatBytes(item.result.originalSizeBytes)}
                  <span className={styles.arrow}> → </span>
                  {formatBytes(item.result.outputSizeBytes)}
                </span>
                <span className={styles.resultStat}>
                  {((1 - item.result.outputSizeBytes / item.result.originalSizeBytes) * 100).toFixed(1)}%削減
                </span>
                <span className={`${styles.resultStat} ${item.result.deltaE < 2.0 ? styles.deltaGood : styles.deltaWarn}`}>
                  ΔE: {item.result.deltaE.toFixed(2)}
                  {item.result.deltaE < 2.0 ? ' ✓' : ' △'}
                </span>
                {item.result.correctionsApplied && (
                  <span className={styles.correctionBadge}>自動色補正済み</span>
                )}
              </div>
              <a
                href={getDownloadUrl(item.jobId)}
                download={item.file.name.replace(/\.(ai|psd)$/i, '.jpg')}
                className={styles.downloadLink}
              >
                JPEGをダウンロード
              </a>
            </div>
          </div>
        </div>
      )}

      {item.state === 'failed' && item.error && (
        <div className={styles.conversionItemBody}>
          <p className={styles.itemError}>{item.error}</p>
        </div>
      )}
    </div>
  )
}

export default function App() {
  const [options, setOptions] = useState<ConversionOptions>(DEFAULT_OPTIONS)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const { items, convertAll, reset, isProcessing, allDone } = useMultiConversion()

  const inConversionPhase = items.length > 0

  const handleFilesSelect = (newFiles: File[]) => {
    setSelectedFiles(prev => {
      const combined = [...prev, ...newFiles]
      return combined.slice(0, 10)
    })
  }

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleConvert = () => {
    if (selectedFiles.length > 0) {
      convertAll(selectedFiles, options)
      setSelectedFiles([])
    }
  }

  const handleReset = () => {
    reset()
    setSelectedFiles([])
  }

  const completedItems = items.filter(i => i.state === 'completed' && i.jobId)
  const completedCount = completedItems.length
  const failedCount = items.filter(i => i.state === 'failed').length
  const batchDownloadUrl =
    completedItems.length > 1
      ? getBatchDownloadUrl(completedItems.map(i => i.jobId!))
      : null

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <h1 className={styles.logo}>chroma-sync</h1>
          <p className={styles.tagline}>AI / PSD → JPEG 色味保持変換</p>
        </div>
      </header>

      <main className={styles.main}>
        {!inConversionPhase ? (
          /* 選択フェーズ */
          <div className={styles.grid}>
            <div className={styles.leftColumn}>
              <section className={styles.section}>
                <h2 className={styles.sectionTitle}>ファイルを選択（最大10枚）</h2>
                <FileUpload
                  onFilesSelect={handleFilesSelect}
                  disabled={isProcessing}
                  currentCount={selectedFiles.length}
                />

                {selectedFiles.length > 0 && (
                  <div className={styles.selectedFileList}>
                    <div className={styles.selectedFileListHeader}>
                      <span className={styles.selectedFileCount}>
                        {selectedFiles.length} / 10 枚選択済み
                      </span>
                    </div>
                    {selectedFiles.map((file, index) => (
                      <div key={index} className={styles.selectedFileItem}>
                        <svg
                          className={styles.fileIconSmall}
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                          <polyline points="14 2 14 8 20 8" />
                        </svg>
                        <span className={styles.selectedFileName}>{file.name}</span>
                        <span className={styles.selectedFileSize}>{formatBytes(file.size)}</span>
                        <button
                          onClick={() => removeFile(index)}
                          className={styles.removeButton}
                          aria-label="削除"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {selectedFiles.length > 0 && (
                  <button onClick={handleConvert} className={styles.convertButton}>
                    {selectedFiles.length === 1 ? '変換を開始' : `${selectedFiles.length}枚を一括変換`}
                  </button>
                )}
              </section>
            </div>

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
        ) : (
          /* 変換フェーズ・結果フェーズ */
          <div className={styles.conversionPhase}>
            <div className={styles.conversionPhaseHeader}>
              <div>
                <h2 className={styles.sectionTitle}>変換状況</h2>
                {allDone && (
                  <p className={styles.conversionSummary}>
                    {completedCount > 0 && <span className={styles.summarySuccess}>{completedCount}枚完了</span>}
                    {failedCount > 0 && <span className={styles.summaryFail}> {failedCount}枚失敗</span>}
                  </p>
                )}
              </div>
              {allDone && (
                <div className={styles.phaseActions}>
                  {batchDownloadUrl && (
                    <a
                      href={batchDownloadUrl}
                      download="chroma-sync-results.zip"
                      className={styles.batchDownloadButton}
                    >
                      一括ダウンロード（ZIP）
                    </a>
                  )}
                  <button onClick={handleReset} className={styles.retryButton}>
                    別のファイルを変換
                  </button>
                </div>
              )}
            </div>

            <div className={styles.conversionList}>
              {items.map(item => (
                <ConversionItemCard key={item.id} item={item} />
              ))}
            </div>
          </div>
        )}
      </main>

      <footer className={styles.footer}>
        <p>chroma-sync &copy; 2024 — AI/PSD to JPEG with color fidelity</p>
      </footer>
    </div>
  )
}
