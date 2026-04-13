import { useState, useRef, useCallback } from 'react';

import { InboxOutlined, LoadingOutlined, CheckCircleFilled, WarningOutlined, DeleteOutlined } from '@ant-design/icons';
import { message } from 'antd';

import styles from './FileDropZone.module.css';

interface FileDropZoneProps {
  onFileDrop: (file: File) => void;
  onFilesDrop?: (files: File[]) => void;
  loading?: boolean;
  multiple?: boolean;
}

const ACCEPTED_EXTENSIONS = ['.csv', '.tsv', '.txt', '.xlsx', '.xls'];
const MAX_FILE_SIZE_MB = 500;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
const MAX_FILES = 20;

function getExtension(name: string): string {
  const dot = name.lastIndexOf('.');
  return dot >= 0 ? name.slice(dot).toLowerCase() : '';
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FileDropZone({ onFileDrop, onFilesDrop, loading, multiple }: FileDropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [droppedFile, setDroppedFile] = useState<File | null>(null);
  const [droppedFiles, setDroppedFiles] = useState<File[]>([]);
  const [validationError, setValidationError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const dragCounter = useRef(0);

  const validateFile = useCallback((file: File): string | null => {
    const ext = getExtension(file.name);
    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      return `Unsupported file type "${ext}". Use CSV, TSV, TXT, or Excel files.`;
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return `File "${file.name}" is too large (${formatSize(file.size)}). Maximum is ${MAX_FILE_SIZE_MB} MB.`;
    }
    if (file.size === 0) {
      return `File "${file.name}" is empty.`;
    }
    return null;
  }, []);

  const validateAndSubmitSingle = useCallback(
    (file: File) => {
      setValidationError(null);
      const error = validateFile(file);
      if (error) {
        setValidationError(error);
        message.error(error);
        return;
      }
      setDroppedFile(file);
      onFileDrop(file);
    },
    [onFileDrop, validateFile],
  );

  const validateAndSubmitMultiple = useCallback(
    (fileList: FileList) => {
      setValidationError(null);
      const files = Array.from(fileList);

      if (files.length > MAX_FILES) {
        const msg = `Maximum ${MAX_FILES} files per batch. You selected ${files.length}.`;
        setValidationError(msg);
        message.error(msg);
        return;
      }

      const validFiles: File[] = [];
      const errors: string[] = [];

      for (const file of files) {
        const error = validateFile(file);
        if (error) {
          errors.push(error);
        } else {
          validFiles.push(file);
        }
      }

      if (errors.length > 0 && validFiles.length === 0) {
        const msg = errors[0];
        setValidationError(msg);
        message.error(msg);
        return;
      }

      if (errors.length > 0) {
        message.warning(`${errors.length} file(s) skipped due to validation errors`);
      }

      setDroppedFiles(validFiles);
      onFilesDrop?.(validFiles);
    },
    [onFilesDrop, validateFile],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current += 1;
    if (dragCounter.current === 1) {
      setIsDragOver(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current -= 1;
    if (dragCounter.current === 0) {
      setIsDragOver(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounter.current = 0;
      setIsDragOver(false);

      if (multiple && e.dataTransfer.files.length > 1) {
        validateAndSubmitMultiple(e.dataTransfer.files);
      } else {
        const file = e.dataTransfer.files[0];
        if (file) validateAndSubmitSingle(file);
      }
    },
    [multiple, validateAndSubmitSingle, validateAndSubmitMultiple],
  );

  const handleClick = () => {
    if (!loading) inputRef.current?.click();
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    if (multiple && files.length > 1) {
      validateAndSubmitMultiple(files);
    } else {
      const file = files[0];
      if (file) validateAndSubmitSingle(file);
    }
    e.target.value = '';
  };

  const handleRemoveFile = (index: number) => {
    setDroppedFiles((prev) => {
      const next = prev.filter((_, i) => i !== index);
      if (next.length === 0) {
        setDroppedFile(null);
      }
      onFilesDrop?.(next);
      return next;
    });
  };

  const zoneClassName = [
    styles.dropZone,
    isDragOver ? styles.dropZoneActive : '',
    validationError ? styles.dropZoneError : '',
    loading ? styles.dropZoneLoading : '',
  ]
    .filter(Boolean)
    .join(' ');

  const hasMultipleFiles = multiple && droppedFiles.length > 0;

  return (
    <>
      <div
        className={zoneClassName}
        onDragOver={handleDragOver}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        {loading ? (
          <>
            <LoadingOutlined className={styles.dropIcon} spin />
            <span className={styles.dropText}>
              Processing {hasMultipleFiles ? `${droppedFiles.length} files` : droppedFile?.name ?? 'file'}…
            </span>
            <span className={styles.dropHint}>
              {droppedFile ? formatSize(droppedFile.size) : ''}
            </span>
          </>
        ) : validationError ? (
          <>
            <WarningOutlined className={`${styles.dropIcon} ${styles.errorIcon}`} />
            <span className={styles.dropTextError}>{validationError}</span>
            <span className={styles.dropHint}>Click or drop again to try another file</span>
          </>
        ) : droppedFile && !hasMultipleFiles && !loading ? (
          <>
            <CheckCircleFilled className={`${styles.dropIcon} ${styles.successIcon}`} />
            <span className={styles.dropText}>{droppedFile.name}</span>
            <span className={styles.dropHint}>{formatSize(droppedFile.size)} · Click or drop to replace</span>
          </>
        ) : hasMultipleFiles ? (
          <>
            <CheckCircleFilled className={`${styles.dropIcon} ${styles.successIcon}`} />
            <span className={styles.dropText}>{droppedFiles.length} files selected</span>
            <span className={styles.dropHint}>
              {formatSize(droppedFiles.reduce((s, f) => s + f.size, 0))} total · Click or drop to add more
            </span>
          </>
        ) : (
          <>
            <InboxOutlined className={styles.dropIcon} />
            <span className={styles.dropText}>
              {multiple ? 'Drop files here or click to browse' : 'Drop a file here or click to browse'}
            </span>
            <span className={styles.dropHint}>
              CSV, TSV, TXT, Excel (.xlsx / .xls) · Max {MAX_FILE_SIZE_MB} MB
              {multiple && ` · Up to ${MAX_FILES} files`}
            </span>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS.join(',')}
          multiple={multiple}
          style={{ display: 'none' }}
          onChange={handleChange}
        />
      </div>

      {hasMultipleFiles && !loading && (
        <div className={styles.fileList}>
          {droppedFiles.map((file, i) => (
            <div key={`${file.name}-${i}`} className={styles.fileListItem}>
              <span className={styles.fileListName}>{file.name}</span>
              <span className={styles.fileListSize}>{formatSize(file.size)}</span>
              <button
                className={styles.fileListRemove}
                onClick={(e) => { e.stopPropagation(); handleRemoveFile(i); }}
                title="Remove file"
              >
                <DeleteOutlined />
              </button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
