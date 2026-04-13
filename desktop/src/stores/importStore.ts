import { create } from 'zustand';

import apiClient from '@/utils/apiClient';
import { useStoreStore } from '@/stores/storeStore';

import type {
  BatchFileItem,
  ColumnMapping,
  DataPreview,
  DetectedSchema,
  FileImportStatus,
  UploadFileResponse,
  GoogleSheetsRequest,
  ValidateFileResponse,
} from '@/types/ingestion';

interface MergeResult {
  rows_new: number;
  rows_updated: number;
  rows_skipped: number;
  rows_dropped: number;
  total_processed: number;
}

interface ImportErrorDetail {
  row_number: number | null;
  column_name: string | null;
  error_type: string;
  error_detail: string;
  original_value: string | null;
}

interface ConfirmImportResponse {
  import_id: string;
  store_id: string;
  data_type: string;
  health_score: number;
  health_details: { check: string; score: number; weight: number; issues: string[] }[];
  merge_result: MergeResult;
  lineage_steps: number;
  warnings: string[];
  import_errors: ImportErrorDetail[];
  detection_confidence: number | null;
}

interface ImportState {
  uploading: boolean;
  preview: DataPreview | null;
  detection: DetectedSchema | null;
  mappings: ColumnMapping[];
  uploadedFilePath: string | null;
  uploadedFileHash: string | null;
  hasHeaderRow: boolean;
  selectedSheet: string | null;

  // Multi-file state
  batchFiles: BatchFileItem[];
  batchMode: boolean;

  importing: boolean;
  importResult: ConfirmImportResponse | null;
  batchResults: ConfirmImportResponse[];

  validating: boolean;
  validationResult: ValidateFileResponse | null;

  resetUpload: () => void;
  setHasHeaderRow: (v: boolean) => void;
  setSelectedSheet: (v: string | null) => void;
  updateMapping: (index: number, targetColumn: string | null) => void;
  updateBatchFileMapping: (fileId: string, index: number, targetColumn: string | null) => void;
  updateBatchFileDataType: (fileId: string, dataType: string) => void;
  cancelBatchFile: (fileId: string) => Promise<void>;
  removeBatchFile: (fileId: string) => void;
  uploadFile: (file: File) => Promise<void>;
  uploadFiles: (files: File[]) => Promise<void>;
  confirmImport: () => Promise<void>;
  confirmBatchImport: () => Promise<void>;
  loadSampleData: () => Promise<void>;
  importGoogleSheet: (req: GoogleSheetsRequest) => Promise<void>;
  importGoogleSheetsBatch: (req: GoogleSheetsRequest) => Promise<void>;
  validateFile: () => Promise<void>;
}

export const useImportStore = create<ImportState>()(
  (set, get) => ({
    uploading: false,
    preview: null,
    detection: null,
    mappings: [],
    uploadedFilePath: null,
    uploadedFileHash: null,
    hasHeaderRow: true,
    selectedSheet: null,
    batchFiles: [],
    batchMode: false,
    importing: false,
    importResult: null,
    batchResults: [],
    validating: false,
    validationResult: null,

    resetUpload: () =>
      set({
        preview: null,
        detection: null,
        mappings: [],
        uploadedFilePath: null,
        uploadedFileHash: null,
        hasHeaderRow: true,
        selectedSheet: null,
        importResult: null,
        batchFiles: [],
        batchMode: false,
        batchResults: [],
        validating: false,
        validationResult: null,
      }),

    setHasHeaderRow: (v) => set({ hasHeaderRow: v }),
    setSelectedSheet: (v) => set({ selectedSheet: v }),

    updateMapping: (index: number, targetColumn: string | null) => {
      const mappings = [...get().mappings];
      if (mappings[index]) {
        mappings[index] = {
          ...mappings[index],
          target_column: targetColumn,
          auto_mapped: false,
        };
        set({ mappings });
      }
    },

    updateBatchFileMapping: (fileId: string, index: number, targetColumn: string | null) => {
      const batchFiles = get().batchFiles.map((bf) => {
        if (bf.id !== fileId) return bf;
        const mappings = [...bf.detection.suggested_mappings];
        if (mappings[index]) {
          mappings[index] = { ...mappings[index], target_column: targetColumn, auto_mapped: false };
        }
        return {
          ...bf,
          detection: { ...bf.detection, suggested_mappings: mappings },
        };
      });
      set({ batchFiles });
    },

    updateBatchFileDataType: (fileId: string, dataType: string) => {
      const batchFiles = get().batchFiles.map((bf) => {
        if (bf.id !== fileId) return bf;
        return {
          ...bf,
          detection: { ...bf.detection, data_type: dataType as BatchFileItem['detection']['data_type'] },
        };
      });
      set({ batchFiles });
    },

    cancelBatchFile: async (fileId: string) => {
      const bf = get().batchFiles.find((f) => f.id === fileId);
      if (!bf) return;
      try {
        await apiClient.delete('/ingestion/cancel-file', {
          params: { file_path: bf.file_path },
        });
      } catch {
        // Non-critical: file may already be removed
      }
      set({
        batchFiles: get().batchFiles.map((f) =>
          f.id === fileId ? { ...f, status: 'cancelled' as FileImportStatus } : f,
        ),
      });
    },

    removeBatchFile: (fileId: string) => {
      set({ batchFiles: get().batchFiles.filter((f) => f.id !== fileId) });
    },

    uploadFile: async (file: File) => {
      set({ uploading: true, batchMode: false });
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('has_header_row', String(get().hasHeaderRow));
        if (get().selectedSheet) {
          formData.append('selected_sheet', get().selectedSheet!);
        }

        const res = await apiClient.post<{ success: boolean; data: UploadFileResponse }>(
          '/ingestion/upload-file',
          formData,
          { headers: { 'Content-Type': 'multipart/form-data' } },
        );

        if (res.data.success && res.data.data) {
          const { preview, detection, file_path, file_hash } = res.data.data;
          set({
            preview,
            detection,
            mappings: detection.suggested_mappings,
            uploadedFilePath: file_path,
            uploadedFileHash: file_hash,
          });
        }
      } finally {
        set({ uploading: false });
      }
    },

    uploadFiles: async (files: File[]) => {
      set({ uploading: true, batchMode: true, batchFiles: [] });
      try {
        const formData = new FormData();
        for (const file of files) {
          formData.append('files', file);
        }
        formData.append('has_header_row', String(get().hasHeaderRow));

        const res = await apiClient.post<{ success: boolean; data: UploadFileResponse[] }>(
          '/ingestion/upload-files',
          formData,
          { headers: { 'Content-Type': 'multipart/form-data' } },
        );

        if (res.data.success && res.data.data) {
          const batchFiles: BatchFileItem[] = res.data.data.map((item, i) => ({
            id: `batch-${Date.now()}-${i}`,
            fileName: files[i]?.name ?? `File ${i + 1}`,
            preview: item.preview,
            detection: item.detection,
            file_path: item.file_path,
            file_hash: item.file_hash,
            status: 'ready' as FileImportStatus,
            error: null,
            mixed_types: item.mixed_types ?? null,
            warnings: item.warnings ?? [],
          }));
          set({ batchFiles });
        }
      } finally {
        set({ uploading: false });
      }
    },

    confirmImport: async () => {
      const { mappings, detection, uploadedFilePath, uploadedFileHash, hasHeaderRow, selectedSheet } = get();
      if (!detection || !uploadedFilePath) return;

      const storeId = useStoreStore.getState().activeStoreId;
      if (!storeId) return;

      set({ importing: true });
      try {
        const res = await apiClient.post<{ success: boolean; data: ConfirmImportResponse }>(
          '/ingestion/confirm-import',
          {
            file_path: uploadedFilePath,
            store_id: storeId,
            data_type: detection.data_type,
            mappings,
            has_header_row: hasHeaderRow,
            selected_sheet: selectedSheet,
            file_hash: uploadedFileHash,
            merge_strategy: 'upsert',
          },
        );

        if (res.data.success && res.data.data) {
          set({ importResult: res.data.data });
        }
      } finally {
        set({ importing: false });
      }
    },

    confirmBatchImport: async () => {
      const { batchFiles, hasHeaderRow } = get();
      const activeFiles = batchFiles.filter((f) => f.status !== 'cancelled');
      if (activeFiles.length === 0) return;

      const storeId = useStoreStore.getState().activeStoreId;
      if (!storeId) return;

      // Mark all active files as importing
      set({
        importing: true,
        batchResults: [],
        batchFiles: batchFiles.map((bf) =>
          bf.status === 'cancelled' ? bf : { ...bf, status: 'importing' as FileImportStatus },
        ),
      });
      try {
        const items = activeFiles.map((bf) => ({
          file_path: bf.file_path,
          store_id: storeId,
          data_type: bf.detection.data_type,
          mappings: bf.detection.suggested_mappings,
          has_header_row: hasHeaderRow,
          file_hash: bf.file_hash,
          merge_strategy: 'upsert',
        }));

        const res = await apiClient.post<{ success: boolean; data: ConfirmImportResponse[]; error?: { code: string; detail: string } }>(
          `/ingestion/confirm-batch-import?store_id=${encodeURIComponent(storeId)}`,
          items,
        );

        if (res.data.data) {
          const results = res.data.data;
          // Mark files as success/error based on results
          set({
            batchResults: results,
            importResult: results[0] ?? null,
            batchFiles: batchFiles.map((bf) => {
              if (bf.status === 'cancelled') return bf;
              const matchingResult = results.find((r) => r.data_type === bf.detection.data_type);
              return {
                ...bf,
                status: matchingResult ? 'success' as FileImportStatus : 'error' as FileImportStatus,
                error: matchingResult ? null : res.data.error?.detail ?? 'Import failed',
              };
            }),
          });
        }
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : 'Import failed';
        set({
          batchFiles: batchFiles.map((bf) =>
            bf.status === 'cancelled' ? bf : { ...bf, status: 'error' as FileImportStatus, error: errorMsg },
          ),
        });
      } finally {
        set({ importing: false });
      }
    },

    loadSampleData: async () => {
      const storeId = useStoreStore.getState().activeStoreId;
      if (!storeId) return;

      set({ importing: true });
      try {
        const res = await apiClient.post<{ success: boolean; data: ConfirmImportResponse }>(
          `/ingestion/load-sample?store_id=${encodeURIComponent(storeId)}`,
        );

        if (res.data.success && res.data.data) {
          set({ importResult: res.data.data });
        }
      } finally {
        set({ importing: false });
      }
    },

    importGoogleSheet: async (req: GoogleSheetsRequest) => {
      set({ importing: true, importResult: null });
      try {
        const res = await apiClient.post<{ success: boolean; data: ConfirmImportResponse }>(
          '/ingestion/import-google-sheet',
          req,
        );
        if (res.data.success && res.data.data) {
          set({ importResult: res.data.data });
        }
      } finally {
        set({ importing: false });
      }
    },

    importGoogleSheetsBatch: async (req: GoogleSheetsRequest) => {
      set({ importing: true, importResult: null, batchResults: [] });
      try {
        const res = await apiClient.post<{ success: boolean; data: ConfirmImportResponse[] }>(
          '/ingestion/import-google-sheets-batch',
          req,
        );
        if (res.data.success && res.data.data) {
          set({
            batchResults: res.data.data,
            importResult: res.data.data[0] ?? null,
          });
        }
      } finally {
        set({ importing: false });
      }
    },

    validateFile: async () => {
      const { detection, uploadedFilePath, mappings, hasHeaderRow, selectedSheet } = get();
      if (!detection || !uploadedFilePath) return;

      set({ validating: true, validationResult: null });
      try {
        const res = await apiClient.post<{ success: boolean; data: ValidateFileResponse }>(
          '/ingestion/validate',
          {
            file_path: uploadedFilePath,
            data_type: detection.data_type,
            mappings,
            has_header_row: hasHeaderRow,
            selected_sheet: selectedSheet,
          },
        );

        if (res.data.success && res.data.data) {
          set({ validationResult: res.data.data });
        }
      } finally {
        set({ validating: false });
      }
    },
  }),
);
