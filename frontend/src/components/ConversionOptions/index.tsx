import React from 'react'
import type { ConversionOptions } from '@/types/conversion'
import styles from './ConversionOptions.module.css'

interface Props {
  options: ConversionOptions
  onChange: (options: ConversionOptions) => void
  disabled?: boolean
}

export const ConversionOptionsPanel: React.FC<Props> = ({ options, onChange, disabled = false }) => {
  const update = (partial: Partial<ConversionOptions>) => {
    onChange({ ...options, ...partial })
  }

  return (
    <div className={styles.panel}>
      <h3 className={styles.title}>変換オプション</h3>

      <div className={styles.group}>
        <label className={styles.label}>
          JPEG品質
          <span className={styles.value}>{options.quality}</span>
        </label>
        <input
          type="range"
          min={1}
          max={100}
          value={options.quality}
          onChange={(e) => update({ quality: Number(e.target.value) })}
          disabled={disabled}
          className={styles.slider}
        />
        <div className={styles.sliderLabels}>
          <span>低（小サイズ）</span>
          <span>高（高品質）</span>
        </div>
      </div>

      <div className={styles.group}>
        <label className={styles.label}>目標ファイルサイズ（KB）</label>
        <div className={styles.inputRow}>
          <input
            type="number"
            min={10}
            max={10240}
            placeholder="例: 500"
            value={options.targetSizeKb ?? ''}
            onChange={(e) => update({ targetSizeKb: e.target.value ? Number(e.target.value) : undefined })}
            disabled={disabled}
            className={styles.numberInput}
          />
          <span className={styles.unit}>KB</span>
        </div>
        <p className={styles.hint}>指定した場合、品質設定より優先されます</p>
      </div>

      <div className={styles.group}>
        <label className={styles.label}>
          許容色差（ΔE）
          <span className={styles.value}>{options.maxDeltaE.toFixed(1)}</span>
        </label>
        <input
          type="range"
          min={0.5}
          max={5.0}
          step={0.1}
          value={options.maxDeltaE}
          onChange={(e) => update({ maxDeltaE: Number(e.target.value) })}
          disabled={disabled}
          className={styles.slider}
        />
        <div className={styles.sliderLabels}>
          <span>厳密（遅い）</span>
          <span>緩い（速い）</span>
        </div>
        <p className={styles.hint}>ΔE &lt; 2.0 が人間の知覚限界の目安です</p>
      </div>

    </div>
  )
}
