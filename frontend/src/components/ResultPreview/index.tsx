import React from 'react'
import type { ConversionResult } from '@/types/conversion'
import { getDownloadUrl, getPreviewUrl } from '@/api/client'
import styles from './ResultPreview.module.css'

interface Props {
  jobId: string
  result: ConversionResult
  originalFileName: string
  onReset: () => void
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export const ResultPreview: React.FC<Props> = ({ jobId, result, originalFileName, onReset }) => {
  const previewUrl = getPreviewUrl(jobId)
  const downloadUrl = getDownloadUrl(jobId)
  const compressionRatio = ((1 - result.outputSizeBytes / result.originalSizeBytes) * 100).toFixed(1)

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>変換完了</h3>
        <button onClick={onReset} className={styles.resetButton}>
          別のファイルを変換
        </button>
      </div>

      {/* プレビュー画像 */}
      <div className={styles.previewSection}>
        <img
          src={previewUrl}
          alt="変換結果プレビュー"
          className={styles.previewImage}
        />
      </div>

      {/* 変換結果の統計 */}
      <div className={styles.stats}>
        <div className={styles.statItem}>
          <span className={styles.statLabel}>元のサイズ</span>
          <span className={styles.statValue}>{formatBytes(result.originalSizeBytes)}</span>
        </div>
        <div className={styles.statItem}>
          <span className={styles.statLabel}>変換後サイズ</span>
          <span className={styles.statValue}>{formatBytes(result.outputSizeBytes)}</span>
        </div>
        <div className={styles.statItem}>
          <span className={styles.statLabel}>圧縮率</span>
          <span className={styles.statValue}>{compressionRatio}%削減</span>
        </div>
        <div className={styles.statItem}>
          <span className={styles.statLabel}>最終色差 (ΔE)</span>
          <span className={`${styles.statValue} ${result.deltaE < 2.0 ? styles.good : styles.warning}`}>
            {result.deltaE.toFixed(2)}
            {result.deltaE < 2.0 ? ' ✓' : ' △'}
          </span>
        </div>
      </div>

      {/* 色補正情報 */}
      {result.correctionsApplied && (
        <div className={styles.correctionInfo}>
          <span className={styles.correctionBadge}>自動色補正適用済み</span>
          <span className={styles.correctionDetail}>
            {result.correctionRegionsCount}箇所の領域を補正しました
          </span>
        </div>
      )}

      {/* 警告（ΔEが閾値超え） */}
      {result.deltaE >= 2.0 && (
        <div className={styles.warning}>
          色補正の精度が目標値に達しませんでした（ΔE: {result.deltaE.toFixed(2)}）。
          ダウンロードして確認いただき、必要に応じて手動で調整してください。
        </div>
      )}

      {/* ダウンロードボタン */}
      <a
        href={downloadUrl}
        download={originalFileName.replace(/\.(ai|psd)$/i, '.jpg')}
        className={styles.downloadButton}
      >
        JPEGをダウンロード
      </a>
    </div>
  )
}
