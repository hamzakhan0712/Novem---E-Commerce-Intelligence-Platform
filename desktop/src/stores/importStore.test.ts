import { describe, it, expect, beforeEach } from 'vitest';
import { useImportStore } from '@/stores/importStore';

describe('importStore', () => {
  beforeEach(() => {
    useImportStore.getState().resetUpload();
  });

  it('has correct default state', () => {
    const state = useImportStore.getState();
    expect(state.uploading).toBe(false);
    expect(state.importing).toBe(false);
    expect(state.preview).toBeNull();
    expect(state.detection).toBeNull();
    expect(state.mappings).toEqual([]);
    expect(state.hasHeaderRow).toBe(true);
    expect(state.batchMode).toBe(false);
  });

  it('resetUpload clears all upload state', () => {
    useImportStore.setState({
      preview: { columns: [], rows: [], total_rows: 10 } as any,
      detection: { data_type: 'orders' } as any,
      mappings: [{ source_column: 'a', target_column: 'b', auto_mapped: true }] as any,
      importResult: { import_id: 'test' } as any,
    });

    useImportStore.getState().resetUpload();
    const state = useImportStore.getState();
    expect(state.preview).toBeNull();
    expect(state.detection).toBeNull();
    expect(state.mappings).toEqual([]);
    expect(state.importResult).toBeNull();
  });

  it('setHasHeaderRow updates flag', () => {
    useImportStore.getState().setHasHeaderRow(false);
    expect(useImportStore.getState().hasHeaderRow).toBe(false);
  });

  it('updateMapping changes target column', () => {
    useImportStore.setState({
      mappings: [
        { source_column: 'col1', target_column: 'order_id', auto_mapped: true },
        { source_column: 'col2', target_column: 'date', auto_mapped: true },
      ] as any,
    });

    useImportStore.getState().updateMapping(0, 'customer_id');
    const mappings = useImportStore.getState().mappings;
    expect(mappings[0].target_column).toBe('customer_id');
    expect(mappings[0].auto_mapped).toBe(false);
    expect(mappings[1].target_column).toBe('date');
  });

  it('updateMapping ignores invalid index', () => {
    useImportStore.setState({
      mappings: [
        { source_column: 'col1', target_column: 'order_id', auto_mapped: true },
      ] as any,
    });

    useImportStore.getState().updateMapping(5, 'customer_id');
    expect(useImportStore.getState().mappings[0].target_column).toBe('order_id');
  });

  it('setSelectedSheet updates sheet', () => {
    useImportStore.getState().setSelectedSheet('Sheet2');
    expect(useImportStore.getState().selectedSheet).toBe('Sheet2');
  });

  it('removeBatchFile removes by id', () => {
    useImportStore.setState({
      batchFiles: [
        { id: 'f1', file_path: '/tmp/a.csv' } as any,
        { id: 'f2', file_path: '/tmp/b.csv' } as any,
      ],
    });

    useImportStore.getState().removeBatchFile('f1');
    const files = useImportStore.getState().batchFiles;
    expect(files.length).toBe(1);
    expect(files[0].id).toBe('f2');
  });
});
