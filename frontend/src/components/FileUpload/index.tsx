import React, { useCallback, useState } from 'react'
import styles from './FileUpload.module.css'

interface Props {
  onFilesSelect: (files: File[]) => void
  disabled?: boolean
  currentCount?: number
}

const MAX_FILES = 10
const ACCEPTED_EXTENSIONS = ['.ai', '.psd']

export const FileUpload: React.FC<Props> = ({
  onFilesSelect,
  disabled = false,
  currentCount = 0,
}) => {
  const [isDragging, setIsDragging] = useState(false)
  const [validationErrors, setValidationErrors] = useState<string[]>([])

  const validateFiles = (rawFiles: File[]): File[] => {
    const errors: string[] = []
    const valid: File[] = []

    const remaining = MAX_FILES - currentCount
    if (rawFiles.length > remaining) {
      errors.push(
        `選択できるファイルは残り${remaining}枚です（最大${MAX_FILES}枚）。先頭${remaining}枚を使用します。`
      )
    }

    const candidates = rawFiles.slice(0, remaining)
    for (const file of candidates) {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase()
      if (!ACCEPTED_EXTENSIONS.includes(ext)) {
        errors.push(`「${file.name}」は対応していない形式です（対応形式: .ai, .psd）`)
        continue
      }
      if (file.size > 100 * 1024 * 1024) {
        errors.push(`「${file.name}」は100MBを超えています`)
        continue
      }
      valid.push(file)
    }

    setValidationErrors(errors)
    return valid
  }

  const handleFiles = useCallback(
    (rawFiles: File[]) => {
      const valid = validateFiles(rawFiles)
      if (valid.length > 0) onFilesSelect(valid)
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [onFilesSelect, currentCount]
  )

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      setIsDragging(false)
      if (disabled) return
      handleFiles(Array.from(e.dataTransfer.files))
    },
    [disabled, handleFiles]
  )

  const handleDragOver = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      if (!disabled) setIsDragging(true)
    },
    [disabled]
  )

  const handleDragLeave = useCallback(() => {
    setIsDragging(false)
  }, [])

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) handleFiles(Array.from(e.target.files))
      e.target.value = ''
    },
    [handleFiles]
  )

  const isFull = currentCount >= MAX_FILES

  return (
    <div className={styles.container}>
      <div
        className={`${styles.dropzone} ${isDragging ? styles.dragging : ''} ${disabled || isFull ? styles.disabled : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <div className={styles.content}>
          <div className={styles.icon}>
            <svg
              width="48"
              height="48"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <p className={styles.mainText}>
            {isFull ? `最大${MAX_FILES}枚に達しました` : 'AI / PSD ファイルをドラッグ＆ドロップ'}
          </p>
          <p className={styles.subText}>{isFull ? '変換してから追加できます' : 'または'}</p>
          {!isFull && (
            <label className={`${styles.button} ${disabled ? styles.disabled : ''}`}>
              ファイルを選択（複数可）
              <input
                type="file"
                accept={ACCEPTED_EXTENSIONS.join(',')}
                onChange={handleInputChange}
                disabled={disabled}
                multiple
                hidden
              />
            </label>
          )}
          <p className={styles.hint}>
            対応形式: .ai, .psd（各最大100MB）最大{MAX_FILES}枚
          </p>
        </div>
      </div>

      {validationErrors.length > 0 && (
        <ul className={styles.errorList}>
          {validationErrors.map((err, i) => (
            <li key={i} className={styles.error}>
              {err}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
