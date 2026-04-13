import { useState } from 'react';

import { Button, Select, Alert, Segmented } from 'antd';
import {
  DownloadOutlined,
  CheckCircleOutlined,
  CrownOutlined,
  BarChartOutlined,
  ExperimentOutlined,
  FundOutlined,
  AlertOutlined,
  RocketOutlined,
  TeamOutlined,
  ShoppingOutlined,
  SmileOutlined,
  HeartOutlined,
  BulbOutlined,
} from '@ant-design/icons';

import { useReportGenerator } from '@/hooks/useReportGenerator';
import { DataGate } from '@/components/shared';

import styles from './Reports.module.css';

const PERIOD_OPTIONS = [
  { label: '7 days', value: '7d' },
  { label: '14 days', value: '14d' },
  { label: '30 days', value: '30d' },
  { label: '60 days', value: '60d' },
  { label: '90 days', value: '90d' },
  { label: '6 months', value: '6m' },
  { label: '12 months', value: '12m' },
];

const MODE_OPTIONS = [
  { value: 'technical', label: 'Technical Analysis', icon: <BarChartOutlined /> },
  { value: 'ceo', label: 'CEO Brief', icon: <CrownOutlined /> },
];

const REPORT_SECTIONS = [
  { icon: <BulbOutlined />, title: 'Executive Summary', desc: 'AI narrative of business state' },
  { icon: <BarChartOutlined />, title: 'KPI Overview', desc: 'Revenue, orders, customers, avg. order value' },
  { icon: <ExperimentOutlined />, title: 'Root Cause Analysis', desc: 'What drove revenue changes' },
  { icon: <AlertOutlined />, title: 'Key Problems', desc: 'Unusual activity & missed revenue' },
  { icon: <RocketOutlined />, title: 'Recommended Actions', desc: 'Rank, $ potential, effort level' },
  { icon: <FundOutlined />, title: 'Forecast Summary', desc: 'Trend outlook with confidence' },
  { icon: <TeamOutlined />, title: 'Customer Health', desc: 'Returning rate, value, at-risk' },
  { icon: <ShoppingOutlined />, title: 'Product Performance', desc: 'Top sellers, revenue mix' },
  { icon: <SmileOutlined />, title: 'Review Insights', desc: 'Review health & brand perception' },
  { icon: <HeartOutlined />, title: 'Health Breakdown', desc: 'Component scores explained' },
];

type ReportMode = 'technical' | 'ceo';
type ReportPeriod = '7d' | '14d' | '30d' | '60d' | '90d' | '6m' | '12m';

export default function Reports() {
  const [mode, setMode] = useState<ReportMode>('technical');
  const [period, setPeriod] = useState<ReportPeriod>('30d');
  const { generating, error, lastFilename, generate } = useReportGenerator();

  return (
    <DataGate pageKey="reports" className={styles.page}>
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>Intelligence Reports</h1>
          <span className={styles.subtitle}>Generate a full AI-powered business analysis report as a branded PDF</span>
        </div>
      </div>

      {/* ── Configure section ── */}
      <div className={styles.configPanel}>
        <div className={styles.configRow}>
          <div className={styles.configField}>
            <span className={styles.fieldLabel}>Report Mode</span>
            <Segmented
              value={mode}
              onChange={(v) => setMode(v as ReportMode)}
              options={MODE_OPTIONS.map((o) => ({
                value: o.value,
                label: (
                  <span className={styles.segmentLabel}>
                    {o.icon} {o.label}
                  </span>
                ),
              }))}
            />
          </div>
          <div className={styles.configField}>
            <span className={styles.fieldLabel}>Analysis Period</span>
            <Select
              value={period}
              onChange={(v) => setPeriod(v as ReportPeriod)}
              options={PERIOD_OPTIONS}
              style={{ width: 160 }}
            />
          </div>
          <div className={styles.generateField}>
            <Button
              type="primary"
              size="large"
              icon={<DownloadOutlined />}
              loading={generating}
              onClick={() => generate(period, mode)}
            >
              {generating ? 'Generating…' : 'Generate PDF'}
            </Button>
          </div>
        </div>

        {error && (
          <Alert type="error" message="Generation failed" description={error} showIcon closable style={{ marginTop: 16 }} />
        )}

        {lastFilename && (
          <div className={styles.successBanner}>
            <CheckCircleOutlined />
            <span>Report saved: <strong>{lastFilename}</strong></span>
          </div>
        )}
      </div>

      {/* ── Mode description ── */}
      <div className={styles.modeHint}>
        {mode === 'technical'
          ? 'Detailed metrics, full breakdowns, percentages, and data-driven narrative. Best for analysts and data teams.'
          : 'Simple language, key decisions only, no jargon. Built for executives and stakeholders.'}
      </div>

      {/* ── Sections preview ── */}
      <div className={styles.sectionsPanel}>
        <span className={styles.sectionsPanelLabel}>Report Sections</span>
        <div className={styles.sectionsGrid}>
          {REPORT_SECTIONS.map((s) => (
            <div key={s.title} className={styles.sectionItem}>
              <span className={styles.sectionIcon}>{s.icon}</span>
              <div className={styles.sectionText}>
                <span className={styles.sectionTitle}>{s.title}</span>
                <span className={styles.sectionDesc}>{s.desc}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
    </DataGate>
  );
}
