import React, { useCallback, useState } from 'react'
import styles from './FileUpload.module.css'

interface Props {
  onFileSelect: (file: File) => void
  disabled?: boolean
}

const ACCEPTED_EXTENSIONS = ['.ai', '.psd']
const ACCEPTED_MIME = [
  'application/postscript',
  'application/illustrator',
  'image/vnd.adobe.photoshop',
  'application/octet-stream',
]

export const FileUpload: React.FC<Props> = ({ onFileSelect, disabled = false }) => {
  const [isDragging, setIsDragging] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)

  const validateFile = (file: File): boolean => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      setValidationError(`対応していないファイル形式です。対応形式: ${ACCEPTED_EXTENSIONS.join(', ')}`)
      return false
    }
    if (file.size > 100 * 1024 * 1024) {
      setValidationError('ファイルサイズが100MBを超えています')
      return false
    }
    setValidationError(null)
    return true
  }

  const handleFile = useCallback(
    (file: File) => {
      if (validateFile(file)) {
        onFileSelect(file)
      }
    },
    [onFileSelect]
  )

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      setIsDragging(false)
      if (disabled) return

      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [disabled, handleFile]
  )

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    if (!disabled) setIsDragging(true)
  }, [disabled])

  const handleDragLeave = useCallback(() => {
    setIsDragging(false)
  }, [])

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) handleFile(file)
      // 同じファイルを再選択できるようにリセット
      e.target.value = ''
    },
    [handleFile]
  )

  return (
    <div className={styles.container}>
      <div
        className={`${styles.dropzone} ${isDragging ? styles.dragging : ''} ${disabled ? styles.disabled : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <div className={styles.content}>
          <div className={styles.icon}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <p className={styles.mainText}>
            AI / PSD ファイルをドラッグ＆ドロップ
          </p>
          <p className={styles.subText}>または</p>
          <label className={styles.button}>
            ファイルを選択
            <input
              type="file"
              accept={ACCEPTED_EXTENSIONS.join(',')}
              onChange={handleInputChange}
              disabled={disabled}
              hidden
            />
          </label>
          <p className={styles.hint}>対応形式: .ai, .psd（最大100MB）</p>
        </div>
      </div>

      {validationError && (
        <p className={styles.error}>{validationError}</p>
      )}
    </div>
  )
}
