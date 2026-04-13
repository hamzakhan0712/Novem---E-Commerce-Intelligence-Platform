import { useState, useEffect, useCallback, useRef } from 'react';

import apiClient from '@/utils/apiClient';
import { useStoreStore } from '@/stores/storeStore';
import { useSyncStore } from '@/stores/syncStore';

interface BrowseResult {
  columns: string[];
  rows: Record<string, unknown>[];
  total: number;
  page: number;
  page_size: number;
}

interface ColumnInfo {
  name: string;
  type: string;
  null_count: number;
  distinct_count: number;
  null_pct: number;
}

interface TableCounts {
  [table: string]: number;
}

interface UseDataViewerReturn {
  tables: TableCounts;
  activeTable: string;
  setActiveTable: (t: string) => void;
  data: BrowseResult | null;
  columnInfo: ColumnInfo[];
  loading: boolean;
  loadingTables: boolean;
  search: string;
  setSearch: (s: string) => void;
  page: number;
  setPage: (p: number) => void;
  pageSize: number;
  setPageSize: (ps: number) => void;
  sortBy: string | null;
  setSortBy: (col: string | null) => void;
  sortDir: 'asc' | 'desc';
  setSortDir: (d: 'asc' | 'desc') => void;
  pinnedColumns: string[];
  togglePin: (col: string) => void;
  hiddenColumns: string[];
  toggleHidden: (col: string) => void;
  refresh: () => void;
  hasStore: boolean;
}

export function useDataViewer(): UseDataViewerReturn {
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const lastSyncTick = useSyncStore((s) => s.lastSyncTick);
  const hasStore = Boolean(activeStoreId);

  const [tables, setTables] = useState<TableCounts>({});
  const [loadingTables, setLoadingTables] = useState(false);
  const [activeTable, setActiveTable] = useState('orders');
  const [data, setData] = useState<BrowseResult | null>(null);
  const [columnInfo, setColumnInfo] = useState<ColumnInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [sortBy, setSortBy] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [pinnedColumns, setPinnedColumns] = useState<string[]>([]);
  const [hiddenColumns, setHiddenColumns] = useState<string[]>([]);
  const searchTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const togglePin = useCallback((col: string) => {
    setPinnedColumns((prev) => prev.includes(col) ? prev.filter((c) => c !== col) : [...prev, col]);
  }, []);

  const toggleHidden = useCallback((col: string) => {
    setHiddenColumns((prev) => prev.includes(col) ? prev.filter((c) => c !== col) : [...prev, col]);
  }, []);

  const fetchTables = useCallback(async () => {
    if (!activeStoreId) return;
    setLoadingTables(true);
    try {
      const res = await apiClient.get('/data-viewer/tables', { params: { store_id: activeStoreId } });
      setTables(res.data?.data ?? {});
    } catch {
      setTables({});
    } finally {
      setLoadingTables(false);
    }
  }, [activeStoreId]);

  const fetchColumnInfo = useCallback(async () => {
    if (!activeStoreId) return;
    try {
      const res = await apiClient.get('/data-viewer/columns', {
        params: { store_id: activeStoreId, table: activeTable },
      });
      setColumnInfo(res.data?.data ?? []);
    } catch {
      setColumnInfo([]);
    }
  }, [activeStoreId, activeTable]);

  const fetchData = useCallback(async () => {
    if (!activeStoreId) return;
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        store_id: activeStoreId,
        table: activeTable,
        page,
        page_size: pageSize,
        sort_dir: sortDir,
      };
      if (sortBy) params.sort_by = sortBy;
      if (search) params.search = search;
      const res = await apiClient.get('/data-viewer/browse', { params });
      setData(res.data?.data ?? null);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [activeStoreId, activeTable, page, pageSize, sortBy, sortDir, search]);

  useEffect(() => {
    fetchTables();
  }, [fetchTables, lastSyncTick]);

  useEffect(() => {
    fetchColumnInfo();
    setPinnedColumns([]);
    setHiddenColumns([]);
  }, [fetchColumnInfo]);

  useEffect(() => {
    setPage(1);
  }, [activeTable, search]);

  useEffect(() => {
    fetchData();
  }, [fetchData, lastSyncTick]);

  const debouncedSetSearch = useCallback((s: string) => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => setSearch(s), 300);
  }, []);

  return {
    tables,
    activeTable,
    setActiveTable,
    data,
    columnInfo,
    loading,
    loadingTables,
    search,
    setSearch: debouncedSetSearch,
    page,
    setPage,
    pageSize,
    setPageSize,
    sortBy,
    setSortBy,
    sortDir,
    setSortDir,
    pinnedColumns,
    togglePin,
    hiddenColumns,
    toggleHidden,
    refresh: fetchData,
    hasStore,
  };
}
