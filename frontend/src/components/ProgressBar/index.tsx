import React from 'react'
import type { ConversionProgress } from '@/types/conversion'
import type { ConversionState } from '@/hooks/useConversion'
import styles from './ProgressBar.module.css'

interface Props {
  progress: ConversionProgress | null
  state?: ConversionState
}

export const ProgressBar: React.FC<Props> = ({ progress, state }) => {
  const percent = progress?.progress ?? 0
  const message =
    progress?.message ??
    (state === 'uploading' ? 'ファイルをアップロード中...' : '変換処理を開始しています...')

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.message}>{message}</span>
        <span className={styles.percent}>{percent}%</span>
      </div>

      <div className={styles.track}>
        <div
          className={`${styles.fill} ${percent === 0 ? styles.indeterminate : ''}`}
          style={percent > 0 ? { width: `${percent}%` } : undefined}
        />
      </div>

      {progress?.deltaE !== undefined && (
        <div className={styles.deltaE}>
          <span className={styles.deltaELabel}>色差 (ΔE):</span>
          <span className={`${styles.deltaEValue} ${progress.deltaE < 2.0 ? styles.good : styles.warning}`}>
            {progress.deltaE.toFixed(2)}
          </span>
          {progress.deltaE < 2.0 ? (
            <span className={styles.badge + ' ' + styles.badgeGood}>許容範囲内</span>
          ) : (
            <span className={styles.badge + ' ' + styles.badgeWarning}>補正中</span>
          )}
        </div>
      )}
    </div>
  )
}
