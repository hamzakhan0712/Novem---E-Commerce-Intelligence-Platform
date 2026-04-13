import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  Button, Form, Input, Select, message, Tag,
} from 'antd';
import {
  FileAddOutlined, GoogleOutlined,
  ExperimentOutlined,
  CheckCircleFilled,
  InfoCircleOutlined,
  ShopOutlined,
  DatabaseOutlined,
  CloudUploadOutlined,
  HistoryOutlined,
  ApiOutlined,
  CloseCircleOutlined,
  DeleteOutlined,
  LoadingOutlined,
  WarningOutlined,
  SafetyCertificateOutlined,
  UndoOutlined,
} from '@ant-design/icons';

import { useImportStore } from '@/stores/importStore';
import { useStoreStore } from '@/stores/storeStore';
import { useSyncStore } from '@/stores/syncStore';
import { useDataAvailabilityStore } from '@/stores/dataAvailabilityStore';
import FileDropZone from '@/components/import/FileDropZone';
import DataPreviewTable from '@/components/import/DataPreviewTable';
import HealthScoreDisplay from '@/components/import/HealthScoreDisplay';
import DataProfilePanel from '@/components/import/DataProfilePanel';
import ImportHistory from '@/components/import/ImportHistory';
import ShopifyConnector from '@/components/import/ShopifyConnector';
import DatabaseConnector from '@/components/import/DatabaseConnector';
import SavedConnectors from '@/components/import/SavedConnectors';
import SyncStatus from '@/components/import/SyncStatus';
import ColumnMapper from '@/components/import/ColumnMapper';
import TemplateDownload from '@/components/import/TemplateDownload';
import SchemaReferencePanel from '@/components/import/SchemaReferencePanel';
import PlatformGuides from '@/components/import/PlatformGuides';
import ValidationPreview from '@/components/import/ValidationPreview';
import DataReadinessPanel from '@/components/import/DataReadinessPanel';
import RollbackPanel from '@/components/import/RollbackPanel';

import type { GoogleSheetsRequest, DataType } from '@/types/ingestion';

import styles from './ImportData.module.css';

type ImportMethod = 'file' | 'google_sheets' | 'sample' | 'shopify' | 'postgresql';
type PageTab = 'import' | 'history' | 'connectors' | 'rollback';

interface MethodDef {
  key: ImportMethod;
  icon: React.ReactNode;
  name: string;
  desc: string;
}

const IMPORT_CATEGORIES: { label: string; methods: MethodDef[] }[] = [
  {
    label: 'Local File-Based',
    methods: [
      { key: 'file', icon: <FileAddOutlined />, name: 'File Upload', desc: 'CSV, TSV, Excel' },
    ],
  },
  {
    label: 'URL-Based',
    methods: [
      { key: 'google_sheets', icon: <GoogleOutlined />, name: 'Google Sheets', desc: 'Public URL' },
    ],
  },
  {
    label: 'API-Based',
    methods: [
      { key: 'shopify', icon: <ShopOutlined />, name: 'Shopify', desc: 'REST Admin API' },
    ],
  },
  {
    label: 'Database-Based',
    methods: [
      { key: 'postgresql', icon: <DatabaseOutlined />, name: 'PostgreSQL', desc: 'Direct connection' },
    ],
  },
  {
    label: 'Demo Data',
    methods: [
      { key: 'sample', icon: <ExperimentOutlined />, name: 'Sample Data', desc: 'Built-in dataset' },
    ],
  },
];

const TAB_DEFS: { key: PageTab; icon: React.ReactNode; label: string }[] = [
  { key: 'import', icon: <CloudUploadOutlined />, label: 'New Import' },
  { key: 'history', icon: <HistoryOutlined />, label: 'History' },
  { key: 'connectors', icon: <ApiOutlined />, label: 'Connectors & Sync' },
  { key: 'rollback', icon: <UndoOutlined />, label: 'Rollback' },
];

export default function ImportData() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<PageTab>('import');
  const [method, setMethod] = useState<ImportMethod>('file');
  const [gsForm] = Form.useForm();

  const importing = useImportStore((s) => s.importing);
  const importResult = useImportStore((s) => s.importResult);
  const preview = useImportStore((s) => s.preview);
  const detection = useImportStore((s) => s.detection);
  const uploading = useImportStore((s) => s.uploading);
  const mappings = useImportStore((s) => s.mappings);
  const batchFiles = useImportStore((s) => s.batchFiles);
  const batchMode = useImportStore((s) => s.batchMode);
  const batchResults = useImportStore((s) => s.batchResults);
  const uploadFile = useImportStore((s) => s.uploadFile);
  const uploadFiles = useImportStore((s) => s.uploadFiles);
  const confirmImport = useImportStore((s) => s.confirmImport);
  const confirmBatchImport = useImportStore((s) => s.confirmBatchImport);
  const loadSampleData = useImportStore((s) => s.loadSampleData);
  const importGoogleSheet = useImportStore((s) => s.importGoogleSheet);
  const importGoogleSheetsBatch = useImportStore((s) => s.importGoogleSheetsBatch);
  const updateMapping = useImportStore((s) => s.updateMapping);
  const cancelBatchFile = useImportStore((s) => s.cancelBatchFile);
  const removeBatchFile = useImportStore((s) => s.removeBatchFile);
  const resetUpload = useImportStore((s) => s.resetUpload);
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const notifyDataChanged = useSyncStore((s) => s.notifyDataChanged);
  const fetchTableCounts = useDataAvailabilityStore((s) => s.fetchTableCounts);
  const updateBatchFileDataType = useImportStore((s) => s.updateBatchFileDataType);
  const validateFile = useImportStore((s) => s.validateFile);
  const validating = useImportStore((s) => s.validating);
  const validationResult = useImportStore((s) => s.validationResult);
  const hasStore = Boolean(activeStoreId);
  const [showMapper, setShowMapper] = useState(false);

  const handleMethodSelect = (m: ImportMethod) => {
    resetUpload();
    setMethod(m);
  };

  const handleFileDrop = (file: File) => {
    uploadFile(file);
  };

  const handleFilesDrop = (files: File[]) => {
    uploadFiles(files);
  };

  const handleConfirmImport = async () => {
    if (batchMode && batchFiles.length > 0) {
      await confirmBatchImport();
      if (useImportStore.getState().batchResults.length > 0) {
        notifyDataChanged();
        if (activeStoreId) await fetchTableCounts(activeStoreId);
        message.success('Batch import complete — redirecting to dashboard');
        navigate('/dashboard');
      }
    } else {
      await confirmImport();
      if (useImportStore.getState().importResult) {
        notifyDataChanged();
        if (activeStoreId) await fetchTableCounts(activeStoreId);
        message.success('Import complete — redirecting to dashboard');
        navigate('/dashboard');
      }
    }
  };

  const handleSampleLoad = async () => {
    try {
      await loadSampleData();
      notifyDataChanged();
      if (activeStoreId) await fetchTableCounts(activeStoreId);
      message.success('Sample data loaded successfully');
      navigate('/dashboard');
    } catch {
      message.error('Failed to load sample data');
    }
  };

  const handleGoogleSheetsImport = async (values: { url: string; sheet_name?: string; sheet_names?: string }) => {
    if (!activeStoreId) return;

    const sheetNamesArr = values.sheet_names
      ? values.sheet_names.split(',').map((s) => s.trim()).filter(Boolean)
      : [];

    if (sheetNamesArr.length > 1) {
      const req: GoogleSheetsRequest = {
        url: values.url,
        sheet_names: sheetNamesArr,
        store_id: activeStoreId,
      };
      try {
        await importGoogleSheetsBatch(req);
        notifyDataChanged();
        if (activeStoreId) await fetchTableCounts(activeStoreId);
        message.success(`Imported ${sheetNamesArr.length} sheets successfully`);
        gsForm.resetFields();
        navigate('/dashboard');
      } catch {
        message.error('Failed to import Google Sheets');
      }
    } else {
      const req: GoogleSheetsRequest = {
        url: values.url,
        sheet_name: sheetNamesArr[0] || values.sheet_name,
        store_id: activeStoreId,
      };
      try {
        await importGoogleSheet(req);
        notifyDataChanged();
        if (activeStoreId) await fetchTableCounts(activeStoreId);
        message.success('Google Sheet imported successfully');
        gsForm.resetFields();
        navigate('/dashboard');
      } catch {
        message.error('Failed to import Google Sheet');
      }
    }
  };

  /* ── Sidebar method item renderer ── */
  const renderMethodItem = (m: MethodDef) => (
    <button
      key={m.key}
      className={`${styles.methodItem} ${method === m.key ? styles.methodItemActive : ''}`}
      onClick={() => handleMethodSelect(m.key)}
    >
      <span className={styles.methodItemIcon}>{m.icon}</span>
      <div className={styles.methodItemText}>
        <span className={styles.methodItemName}>{m.name}</span>
        <span className={styles.methodItemDesc}>{m.desc}</span>
      </div>
    </button>
  );

  /* ── Work area for selected method ── */
  const renderWorkArea = () => {
    if (!hasStore) {
      return (
        <div className={styles.alert} data-variant="warning">
          <InfoCircleOutlined className={styles.alertIcon} />
          <div className={styles.alertContent}>
            <span className={styles.alertTitle}>No store selected</span>
            <span className={styles.alertDesc}>Create a store in the status bar before importing data.</span>
          </div>
        </div>
      );
    }

    switch (method) {
      case 'file':
        return (
          <>
            <h3 className={styles.sectionTitle}>Upload Files</h3>
            <p className={styles.sectionDesc}>
              Drag and drop one or more CSV, TSV, or Excel files — NOVEM will auto-detect the format and data type for each.
            </p>
            {!preview && batchFiles.length === 0 && (
              <>
                <TemplateDownload />
                <SchemaReferencePanel />
                <PlatformGuides />
                <FileDropZone
                  onFileDrop={handleFileDrop}
                  onFilesDrop={handleFilesDrop}
                  loading={uploading}
                  multiple
                />
              </>
            )}

            {/* Single file preview */}
            {preview && detection && !batchMode && (
              <>
                {detection.confidence < 60 && (
                  <div className={styles.alert} data-variant="warning">
                    <WarningOutlined className={styles.alertIcon} />
                    <div className={styles.alertContent}>
                      <span className={styles.alertTitle}>Low detection confidence ({detection.confidence}%)</span>
                      <span className={styles.alertDesc}>
                        Auto-detected as &quot;{detection.data_type}&quot; but this may be wrong. Please verify or change the data type below.
                      </span>
                    </div>
                  </div>
                )}

                <div className={styles.schemaOverview}>
                  <InfoCircleOutlined style={{ color: 'var(--novem-accent)' }} />
                  <span>
                    Detected as{' '}
                    <Select
                      size="small"
                      value={detection.data_type}
                      onChange={(val: DataType) => {
                        useImportStore.setState((s) => ({
                          detection: s.detection ? { ...s.detection, data_type: val } : s.detection,
                        }));
                      }}
                      style={{ width: 130 }}
                      options={[
                        { value: 'orders', label: 'Orders' },
                        { value: 'customers', label: 'Customers' },
                        { value: 'products', label: 'Products' },
                        { value: 'ad_spend', label: 'Ad Spend' },
                        { value: 'reviews', label: 'Reviews' },
                        { value: 'stock_levels', label: 'Stock Levels' },
                      ]}
                    />
                    {' '}with {detection.confidence}% confidence
                    · {preview.total_rows.toLocaleString()} rows
                    · {preview.headers.length} columns
                  </span>
                  <Button
                    size="small"
                    type={showMapper ? 'primary' : 'default'}
                    onClick={() => setShowMapper(!showMapper)}
                    style={{ marginLeft: 'auto' }}
                  >
                    {showMapper ? 'Hide' : 'Edit'} Column Mapping
                  </Button>
                </div>

                {(showMapper || detection.confidence < 70) && (
                  <ColumnMapper
                    mappings={mappings}
                    dataType={detection.data_type}
                    sampleRow={preview.rows[0] ?? []}
                    headers={preview.headers}
                    onMappingChange={updateMapping}
                  />
                )}

                <DataPreviewTable preview={preview} />

                {validationResult && <ValidationPreview result={validationResult} />}

                <div className={styles.formActions}>
                  <Button onClick={resetUpload}>Cancel</Button>
                  <Button
                    icon={<SafetyCertificateOutlined />}
                    loading={validating}
                    onClick={() => validateFile()}
                    disabled={!hasStore}
                  >
                    {validationResult ? 'Re-validate' : 'Validate First'}
                  </Button>
                  <Button type="primary" loading={importing} onClick={handleConfirmImport} disabled={!hasStore}>
                    Confirm Import
                  </Button>
                </div>
              </>
            )}

            {/* Multi-file batch preview */}
            {batchMode && batchFiles.length > 0 && (
              <>
                <div className={styles.schemaOverview}>
                  <InfoCircleOutlined style={{ color: 'var(--novem-accent)' }} />
                  <span>
                    {batchFiles.filter((f) => f.status !== 'cancelled').length} file(s) ready
                    {batchFiles.some((f) => f.status === 'cancelled') && (
                      <> · {batchFiles.filter((f) => f.status === 'cancelled').length} cancelled</>
                    )}
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
                  {batchFiles.map((bf) => {
                    const statusIcon = bf.status === 'success'
                      ? <CheckCircleFilled style={{ color: 'var(--novem-success)' }} />
                      : bf.status === 'error'
                        ? <CloseCircleOutlined style={{ color: 'var(--novem-error)' }} />
                        : bf.status === 'importing'
                          ? <LoadingOutlined style={{ color: 'var(--novem-accent)' }} />
                          : bf.status === 'cancelled'
                            ? <DeleteOutlined style={{ color: 'var(--novem-text-tertiary)' }} />
                            : null;

                    return (
                      <div key={bf.id} style={{
                        display: 'flex', alignItems: 'center', gap: 10,
                        padding: '8px 12px', borderRadius: 'var(--novem-radius)',
                        background: bf.status === 'cancelled' ? 'var(--novem-bg-subtle)' : 'var(--novem-bg-elevated)',
                        border: `1px solid ${bf.status === 'error' ? 'var(--novem-error)' : 'var(--novem-border)'}`,
                        fontSize: 13,
                        opacity: bf.status === 'cancelled' ? 0.5 : 1,
                      }}>
                        {statusIcon}
                        <span style={{ flex: 1, fontWeight: 500 }}>{bf.fileName}</span>
                        <Select
                          size="small"
                          value={bf.detection.data_type}
                          onChange={(val: string) => updateBatchFileDataType(bf.id, val)}
                          disabled={bf.status === 'success' || bf.status === 'importing' || bf.status === 'cancelled'}
                          style={{ width: 120 }}
                          options={[
                            { value: 'orders', label: 'Orders' },
                            { value: 'customers', label: 'Customers' },
                            { value: 'products', label: 'Products' },
                            { value: 'ad_spend', label: 'Ad Spend' },
                            { value: 'reviews', label: 'Reviews' },
                            { value: 'stock_levels', label: 'Stock Levels' },
                          ]}
                        />
                        <span style={{ color: 'var(--novem-text-tertiary)' }}>
                          {bf.detection.confidence}% · {bf.preview.total_rows.toLocaleString()} rows
                        </span>
                        {bf.detection.confidence < 60 && (
                          <Tag color="orange" icon={<WarningOutlined />}>Low confidence</Tag>
                        )}
                        {bf.mixed_types && bf.mixed_types.length > 0 && (
                          <Tag color="blue" icon={<WarningOutlined />}>Mixed: {bf.mixed_types.join(', ')}</Tag>
                        )}
                        {bf.error && (
                          <span style={{ color: 'var(--novem-error)', fontSize: 12 }}>{bf.error}</span>
                        )}
                        {bf.status !== 'success' && bf.status !== 'importing' && bf.status !== 'cancelled' && (
                          <Button
                            size="small"
                            type="text"
                            danger
                            icon={<CloseCircleOutlined />}
                            onClick={() => cancelBatchFile(bf.id)}
                            title="Cancel this file"
                          />
                        )}
                        {bf.status === 'cancelled' && (
                          <Button
                            size="small"
                            type="text"
                            icon={<DeleteOutlined />}
                            onClick={() => removeBatchFile(bf.id)}
                            title="Remove from list"
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className={styles.formActions}>
                  <Button onClick={resetUpload}>Cancel All</Button>
                  <Button
                    type="primary"
                    loading={importing}
                    onClick={handleConfirmImport}
                    disabled={!hasStore || batchFiles.filter((f) => f.status !== 'cancelled').length === 0}
                  >
                    Confirm Import ({batchFiles.filter((f) => f.status !== 'cancelled').length} files)
                  </Button>
                </div>

                {batchResults.length > 0 && (
                  <div style={{ marginTop: 16 }}>
                    {batchResults.map((r, i) => (
                      <div key={i} style={{
                        display: 'flex', alignItems: 'center', gap: 10,
                        padding: '6px 12px', fontSize: 12, marginBottom: 4,
                      }}>
                        <CheckCircleFilled style={{ color: 'var(--novem-success)' }} />
                        <span>{r.data_type}</span>
                        <span>— {r.merge_result.total_processed} rows processed</span>
                        <Tag color={r.health_score >= 80 ? 'success' : 'warning'}>{r.health_score}%</Tag>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </>
        );
      case 'google_sheets':
        return (
          <>
            <h3 className={styles.sectionTitle}>Import from Google Sheets</h3>
            <p className={styles.sectionDesc}>
              Paste the public URL of your Google Sheet. Import a single sheet or multiple sheets at once.
            </p>
            <Form form={gsForm} layout="vertical" onFinish={handleGoogleSheetsImport}>
              <Form.Item name="url" label="Spreadsheet URL" rules={[{ required: true, message: 'Enter the Google Sheets URL' }]}>
                <Input placeholder="https://docs.google.com/spreadsheets/d/..." />
              </Form.Item>
              <Form.Item name="sheet_name" label="Single Sheet Name (optional)">
                <Input placeholder="Sheet1" />
              </Form.Item>
              <Form.Item
                name="sheet_names"
                label="Multiple Sheets (optional)"
                extra="Comma-separated list of sheet names to import, e.g. Orders, Customers, Products"
              >
                <Input placeholder="Orders, Customers, Products" />
              </Form.Item>
              <div className={styles.formActions}>
                <Button type="primary" htmlType="submit" loading={importing} disabled={!hasStore}>Import Sheet(s)</Button>
              </div>
            </Form>
          </>
        );
      case 'sample':
        return (
          <>
            <h3 className={styles.sectionTitle}>Load Sample Dataset</h3>
            <p className={styles.sectionDesc}>
              Load a built-in demo e-commerce dataset with orders, customers, products, reviews, and more — perfect for exploring NOVEM.
            </p>
            <Button type="primary" onClick={handleSampleLoad} loading={importing} disabled={!hasStore}>
              Load Sample Data
            </Button>
          </>
        );
      case 'shopify':
        return <ShopifyConnector />;
      case 'postgresql':
        return <DatabaseConnector />;
      default:
        return null;
    }
  };

  return (
    <div className={styles.page}>
      {/* ── Header ── */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>Import Data</h1>
          <span className={styles.subtitle}>Bring your e-commerce data into NOVEM</span>
        </div>
      </div>

      {/* ── Tab bar ── */}
      <div className={styles.tabBar}>
        {TAB_DEFS.map((t) => (
          <button
            key={t.key}
            className={`${styles.tab} ${tab === t.key ? styles.tabActive : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.icon}
            <span>{t.label}</span>
          </button>
        ))}
      </div>

      {/* ── Tab content ── */}
      <div className={styles.content}>
        {/* ===== NEW IMPORT TAB ===== */}
        {tab === 'import' && (
          <>
            {/* Left-right split */}
            <div className={styles.importSplit}>
              {/* LEFT — method sidebar */}
              <div className={styles.sidebar}>
                {IMPORT_CATEGORIES.map((cat) => (
                  <div key={cat.label} className={styles.methodGroup}>
                    <span className={styles.groupLabel}>{cat.label}</span>
                    {cat.methods.map(renderMethodItem)}
                  </div>
                ))}
              </div>

              {/* RIGHT — form / work area + results */}
              <div className={styles.workPanel}>
                {importResult ? (
                  <>
                    <div className={styles.resultBanner}>
                      <div className={styles.resultHeader}>
                        <CheckCircleFilled className={styles.resultBannerIcon} />
                        <div className={styles.resultInfo}>
                          <span className={styles.resultTitle}>Import Complete</span>
                          <span className={styles.resultMeta}>Your data is ready for analysis</span>
                        </div>
                      </div>
                      <div className={styles.resultStats}>
                        {importResult.merge_result && (
                          <>
                            <div className={styles.resultStat}>
                              <span className={styles.resultStatValue}>{importResult.merge_result.total_processed.toLocaleString()}</span>
                              <span className={styles.resultStatLabel}>Processed</span>
                            </div>
                            <div className={styles.resultStat}>
                              <span className={styles.resultStatValue} style={{ color: 'var(--novem-success)' }}>{importResult.merge_result.rows_new.toLocaleString()}</span>
                              <span className={styles.resultStatLabel}>New</span>
                            </div>
                            <div className={styles.resultStat}>
                              <span className={styles.resultStatValue}>{importResult.merge_result.rows_updated.toLocaleString()}</span>
                              <span className={styles.resultStatLabel}>Updated</span>
                            </div>
                            {importResult.merge_result.rows_dropped > 0 && (
                              <div className={styles.resultStat}>
                                <span className={styles.resultStatValue} style={{ color: 'var(--novem-error)' }}>{importResult.merge_result.rows_dropped.toLocaleString()}</span>
                                <span className={styles.resultStatLabel}>Dropped</span>
                              </div>
                            )}
                          </>
                        )}
                        <div className={styles.resultStat}>
                          <span className={styles.resultStatValue} style={{ color: importResult.health_score >= 80 ? 'var(--novem-success)' : importResult.health_score >= 50 ? 'var(--novem-warning)' : 'var(--novem-error)' }}>
                            {importResult.health_score}%
                          </span>
                          <span className={styles.resultStatLabel}>Quality</span>
                        </div>
                      </div>
                    </div>
                    {importResult.warnings && importResult.warnings.length > 0 && (
                      <div className={styles.alert} data-variant="warning" style={{ marginTop: 12 }}>
                        <WarningOutlined className={styles.alertIcon} />
                        <div className={styles.alertContent}>
                          <span className={styles.alertTitle}>Import Warnings</span>
                          {importResult.warnings.map((w, i) => (
                            <span key={i} className={styles.alertDesc}>{w}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    <HealthScoreDisplay score={importResult.health_score} details={importResult.health_details} />
                    {importResult.store_id && (
                      <DataProfilePanel storeId={importResult.store_id} dataType={importResult.data_type} />
                    )}
                    <DataReadinessPanel />
                  </>
                ) : (
                  renderWorkArea()
                )}
              </div>
            </div>
          </>
        )}

        {/* ===== HISTORY TAB ===== */}
        {tab === 'history' && (
          hasStore ? (
            <ImportHistory />
          ) : (
            <div className={styles.emptyHint}>
              <HistoryOutlined className={styles.emptyHintIcon} />
              <span>Create a store to view import history</span>
            </div>
          )
        )}

        {/* ===== CONNECTORS & SYNC TAB ===== */}
        {tab === 'connectors' && (
          hasStore ? (
            <div className={styles.connectorsLayout}>
              <div className={styles.connectorSection}>
                <h3 className={styles.sectionTitle}>Saved Connectors</h3>
                <p className={styles.sectionDesc}>Manage your connected data sources and trigger manual syncs.</p>
                <SavedConnectors />
              </div>
              <div className={styles.connectorSection}>
                <h3 className={styles.sectionTitle}>Sync Status</h3>
                <p className={styles.sectionDesc}>Active sync schedule and recent sync history.</p>
                <SyncStatus />
              </div>
            </div>
          ) : (
            <div className={styles.emptyHint}>
              <ApiOutlined className={styles.emptyHintIcon} />
              <span>Create a store to manage connectors</span>
            </div>
          )
        )}

        {/* ===== ROLLBACK TAB ===== */}
        {tab === 'rollback' && (
          hasStore ? (
            <div>
              <h3 className={styles.sectionTitle}>Import Snapshots</h3>
              <p className={styles.sectionDesc}>
                Snapshots are taken automatically before each import. Roll back to undo a bad import.
              </p>
              <RollbackPanel />
            </div>
          ) : (
            <div className={styles.emptyHint}>
              <UndoOutlined className={styles.emptyHintIcon} />
              <span>Create a store to manage rollbacks</span>
            </div>
          )
        )}
      </div>
    </div>
  );
}
