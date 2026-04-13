import { useMemo, useState } from 'react';

import { Input, Table, Button, Spin, Tooltip, Drawer, Tag, Dropdown, Pagination } from 'antd';
import {
  ReloadOutlined, SearchOutlined,
  ColumnHeightOutlined, DownloadOutlined,
  EyeInvisibleOutlined, PushpinOutlined,
  InfoCircleOutlined, SettingOutlined,
  TableOutlined, CloseOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { MenuProps } from 'antd';

import { useStoreStore } from '@/stores/storeStore';
import { useDataViewer } from '@/hooks/useDataViewer';
import { DataGate } from '@/components/shared';
import apiClient from '@/utils/apiClient';

import styles from './DataViewer.module.css';

const TABLE_LABELS: Record<string, string> = {
  orders: 'Orders',
  customers: 'Customers',
  products: 'Products',
  ad_spend: 'Ad Spend',
  reviews: 'Reviews',
  stock_levels: 'Stock Levels',
};

const TABLE_ICONS: Record<string, React.ReactNode> = {
  orders: <TableOutlined />,
  customers: <TableOutlined />,
  products: <TableOutlined />,
  ad_spend: <TableOutlined />,
  reviews: <TableOutlined />,
  stock_levels: <TableOutlined />,
};

const TYPE_COLORS: Record<string, string> = {
  INTEGER: 'blue',
  BIGINT: 'blue',
  DOUBLE: 'cyan',
  FLOAT: 'cyan',
  DECIMAL: 'cyan',
  VARCHAR: 'green',
  TEXT: 'green',
  DATE: 'orange',
  TIMESTAMP: 'orange',
  BOOLEAN: 'purple',
};

function getTypeColor(dtype: string): string {
  for (const [key, color] of Object.entries(TYPE_COLORS)) {
    if (dtype.toUpperCase().includes(key)) return color;
  }
  return 'default';
}

function formatColHeader(col: string): string {
  return col.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function DataViewer() {
  const {
    tables, activeTable, setActiveTable,
    data, columnInfo, loading, loadingTables,
    search, setSearch,
    page, setPage, pageSize, setPageSize,
    sortBy, setSortBy, sortDir, setSortDir,
    pinnedColumns, togglePin,
    hiddenColumns, toggleHidden,
    refresh, hasStore,
  } = useDataViewer();

  const [searchInput, setSearchInput] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [density, setDensity] = useState<'small' | 'middle'>('small');
  const [exporting, setExporting] = useState(false);

  const handleSearchChange = (value: string) => {
    setSearchInput(value);
    setSearch(value);
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await apiClient.post('/export/csv', {
        store_id: useStoreStore.getState().activeStoreId,
        data_type: activeTable,
      }, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `${activeTable}_export.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      // silent fail — export endpoint may not support blob
    } finally {
      setExporting(false);
    }
  };

  const densityMenu: MenuProps = {
    items: [
      { key: 'small', label: 'Compact' },
      { key: 'middle', label: 'Comfortable' },
    ],
    onClick: ({ key }) => setDensity(key as 'small' | 'middle'),
    selectedKeys: [density],
  };

  const visibleColumns = useMemo(() => {
    if (!data?.columns) return [];
    return data.columns.filter((c) => c !== 'store_id' && !hiddenColumns.includes(c));
  }, [data?.columns, hiddenColumns]);

  const columns: ColumnsType<Record<string, unknown>> = useMemo(() => {
    const pinned = visibleColumns.filter((c) => pinnedColumns.includes(c));
    const unpinned = visibleColumns.filter((c) => !pinnedColumns.includes(c));
    const ordered = [...pinned, ...unpinned];

    return ordered.map((col) => {
      const ci = columnInfo.find((c) => c.name === col);
      return {
        title: (
          <div className={styles.colHeader}>
            <span>{formatColHeader(col)}</span>
            {ci && (
              <Tooltip title={`${ci.type} · ${ci.distinct_count} unique · ${ci.null_pct}% empty`}>
                <InfoCircleOutlined className={styles.colInfoIcon} />
              </Tooltip>
            )}
            {pinnedColumns.includes(col) && (
              <PushpinOutlined className={styles.colPinIcon} />
            )}
          </div>
        ),
        dataIndex: col,
        key: col,
        ellipsis: true,
        sorter: true,
        sortOrder: sortBy === col ? (sortDir === 'asc' ? 'ascend' as const : 'descend' as const) : undefined,
        fixed: pinnedColumns.includes(col) ? 'left' as const : undefined,
        width: col.includes('id') ? 130 : col.includes('date') || col.includes('_at') ? 170 : undefined,
        render: (val: unknown) => {
          if (val === null || val === undefined) return <span className={styles.nullCell}>Empty</span>;
          if (typeof val === 'number') return <span className={styles.numberCell}>{val.toLocaleString()}</span>;
          if (typeof val === 'boolean') return <Tag color={val ? 'green' : 'default'}>{String(val)}</Tag>;
          const s = String(val);
          if (s.length > 120) return <Tooltip title={s}><span>{s.slice(0, 120)}…</span></Tooltip>;
          return s;
        },
      };
    });
  }, [visibleColumns, sortBy, sortDir, pinnedColumns, columnInfo]);

  if (!hasStore) {
    return (
      <DataGate pageKey="data-viewer" className={styles.page}>
        <div />
      </DataGate>
    );
  }

  const totalRows = Object.values(tables).reduce((a, b) => a + b, 0);

  return (
    <DataGate pageKey="data-viewer" className={styles.page}>
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>Data Viewer</h1>
          <span className={styles.subtitle}>
            {Object.keys(tables).length} tables · {totalRows.toLocaleString()} total rows
          </span>
        </div>
        <div className={styles.headerRight}>
          <Button size="small" icon={<DownloadOutlined />} onClick={handleExport} loading={exporting}>
            Export CSV
          </Button>
        </div>
      </div>

      <div className={styles.body}>
        {/* Sidebar: table list */}
        <div className={styles.sidebar}>
          <span className={styles.sidebarLabel}>Tables</span>
          {loadingTables ? (
            <div className={styles.sidebarLoading}><Spin size="small" /></div>
          ) : (
            Object.entries(tables).map(([tbl, count]) => (
              <button
                key={tbl}
                className={`${styles.tableItem} ${activeTable === tbl ? styles.tableItemActive : ''}`}
                onClick={() => setActiveTable(tbl)}
              >
                <span className={styles.tableItemIcon}>{TABLE_ICONS[tbl]}</span>
                <span className={styles.tableItemName}>{TABLE_LABELS[tbl] ?? tbl}</span>
                <span className={styles.tableCount}>{count.toLocaleString()}</span>
              </button>
            ))
          )}
        </div>

        {/* Content */}
        <div className={styles.content}>
          {/* Toolbar */}
          <div className={styles.toolbar}>
            <div className={styles.toolbarLeft}>
              <Input
                prefix={<SearchOutlined />}
                placeholder={`Search ${TABLE_LABELS[activeTable] ?? activeTable}…`}
                value={searchInput}
                onChange={(e) => handleSearchChange(e.target.value)}
                allowClear
                className={styles.searchInput}
                size="small"
              />
            </div>
            <div className={styles.toolbarRight}>
              {data && (
                <span className={styles.rowCount}>
                  {data.total.toLocaleString()} row{data.total !== 1 ? 's' : ''}
                </span>
              )}
              <Tooltip title="Column settings">
                <Button icon={<SettingOutlined />} size="small" onClick={() => setDrawerOpen(true)} />
              </Tooltip>
              <Dropdown menu={densityMenu} trigger={['click']}>
                <Tooltip title="Row density">
                  <Button icon={<ColumnHeightOutlined />} size="small" />
                </Tooltip>
              </Dropdown>
              <Tooltip title="Refresh">
                <Button icon={<ReloadOutlined />} size="small" onClick={refresh} />
              </Tooltip>
            </div>
          </div>

          {/* Active filters / hidden columns chip bar */}
          {(hiddenColumns.length > 0 || pinnedColumns.length > 0 || search) && (
            <div className={styles.chipBar}>
              {search && (
                <span className={styles.chip}>
                  <SearchOutlined /> &quot;{search}&quot;
                  <button className={styles.chipClose} onClick={() => handleSearchChange('')}><CloseOutlined /></button>
                </span>
              )}
              {pinnedColumns.map((col) => (
                <span key={`pin-${col}`} className={`${styles.chip} ${styles.chipPin}`}>
                  <PushpinOutlined /> {formatColHeader(col)}
                  <button className={styles.chipClose} onClick={() => togglePin(col)}><CloseOutlined /></button>
                </span>
              ))}
              {hiddenColumns.length > 0 && (
                <span className={styles.chip}>
                  <EyeInvisibleOutlined /> {hiddenColumns.length} hidden column{hiddenColumns.length !== 1 ? 's' : ''}
                  <button className={styles.chipClose} onClick={() => hiddenColumns.forEach(toggleHidden)}><CloseOutlined /></button>
                </span>
              )}
            </div>
          )}

          {/* Data table — no built-in pagination, scrollable area */}
          <div className={styles.tableWrapper}>
            <Table
              dataSource={data?.rows ?? []}
              columns={columns}
              loading={loading}
              size={density}
              rowKey={(_, i) => String(i)}
              scroll={{ x: 'max-content' }}
              pagination={false}
              onChange={(_pag, _filt, sorter) => {
                if (!Array.isArray(sorter) && sorter.columnKey) {
                  setSortBy(sorter.columnKey as string);
                  setSortDir(sorter.order === 'ascend' ? 'asc' : 'desc');
                }
              }}
            />
          </div>

          {/* Sticky pagination at the bottom */}
          {data && data.total > 0 && (
            <div className={styles.paginationBar}>
              <span className={styles.paginationInfo}>
                {((page - 1) * pageSize + 1).toLocaleString()}–{Math.min(page * pageSize, data.total).toLocaleString()} of {data.total.toLocaleString()}
              </span>
              <Pagination
                current={page}
                pageSize={pageSize}
                total={data.total}
                showSizeChanger
                pageSizeOptions={['25', '50', '100', '200']}
                size="small"
                onChange={(p, ps) => {
                  setPage(p);
                  setPageSize(ps);
                }}
              />
            </div>
          )}
        </div>
      </div>

      {/* Column settings drawer */}
      <Drawer
        title="Column Settings"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={340}
      >
        <div className={styles.drawerContent}>
          <p className={styles.drawerHint}>Toggle visibility and pin columns to the left edge.</p>
          {columnInfo.map((ci) => (
            <div key={ci.name} className={styles.colRow}>
              <div className={styles.colRowLeft}>
                <button
                  className={`${styles.colVisBtn} ${hiddenColumns.includes(ci.name) ? styles.colVisBtnOff : ''}`}
                  onClick={() => toggleHidden(ci.name)}
                >
                  {hiddenColumns.includes(ci.name) ? <EyeInvisibleOutlined /> : <TableOutlined />}
                </button>
                <div className={styles.colRowInfo}>
                  <span className={styles.colRowName}>{formatColHeader(ci.name)}</span>
                  <Tag color={getTypeColor(ci.type)} className={styles.colTypeTag}>{ci.type}</Tag>
                </div>
              </div>
              <Tooltip title={pinnedColumns.includes(ci.name) ? 'Unpin' : 'Pin to left'}>
                <button
                  className={`${styles.pinBtn} ${pinnedColumns.includes(ci.name) ? styles.pinBtnActive : ''}`}
                  onClick={() => togglePin(ci.name)}
                >
                  <PushpinOutlined />
                </button>
              </Tooltip>
            </div>
          ))}
          {columnInfo.length > 0 && (
            <div className={styles.colStats}>
              <span>{columnInfo.length} columns</span>
              <span>·</span>
              <span>{hiddenColumns.length} hidden</span>
              <span>·</span>
              <span>{pinnedColumns.length} pinned</span>
            </div>
          )}
        </div>
      </Drawer>
    </div>
    </DataGate>
  );
}
