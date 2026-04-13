import { Tag, Progress } from 'antd';
import {
  CheckCircleFilled,
  CloseCircleFilled,
  WarningFilled,
  InfoCircleFilled,
  ThunderboltOutlined,
} from '@ant-design/icons';

import type { ValidateFileResponse } from '@/types/ingestion';

import styles from './ValidationPreview.module.css';

interface Props {
  result: ValidateFileResponse;
}

export default function ValidationPreview({ result }: Props) {
  const scoreColor =
    result.readiness_score >= 80
      ? 'var(--novem-success)'
      : result.readiness_score >= 50
        ? 'var(--novem-warning)'
        : 'var(--novem-error)';

  const errorIssues = result.issues.filter((i) => i.severity === 'error');
  const warningIssues = result.issues.filter((i) => i.severity === 'warning');
  const infoIssues = result.issues.filter((i) => i.severity === 'info');

  return (
    <div className={styles.container}>
      {/* Header with readiness score */}
      <div className={styles.header}>
        <ThunderboltOutlined className={styles.headerIcon} />
        <span className={styles.headerTitle}>Validation Results</span>
        <div className={styles.scoreWrap}>
          <Progress
            type="circle"
            percent={result.readiness_score}
            size={44}
            strokeColor={scoreColor}
            format={(pct) => <span style={{ fontSize: 12, fontWeight: 700 }}>{pct}</span>}
          />
        </div>
      </div>

      {/* Row summary */}
      <div className={styles.rowSummary}>
        <div className={styles.rowStat}>
          <span className={styles.rowStatValue}>{result.total_rows.toLocaleString()}</span>
          <span className={styles.rowStatLabel}>Total Rows</span>
        </div>
        <div className={styles.rowStat}>
          <span className={styles.rowStatValue} style={{ color: 'var(--novem-success)' }}>
            {result.valid_rows.toLocaleString()}
          </span>
          <span className={styles.rowStatLabel}>Will Import</span>
        </div>
        {result.droppable_rows > 0 && (
          <div className={styles.rowStat}>
            <span className={styles.rowStatValue} style={{ color: 'var(--novem-error)' }}>
              {result.droppable_rows.toLocaleString()}
            </span>
            <span className={styles.rowStatLabel}>Will Drop</span>
          </div>
        )}
      </div>

      {/* Missing required columns */}
      {result.missing_required.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <CloseCircleFilled style={{ color: 'var(--novem-error)' }} />
            <span>Missing required columns</span>
          </div>
          <div className={styles.tagList}>
            {result.missing_required.map((col) => (
              <Tag key={col} color="error">{col}</Tag>
            ))}
          </div>
        </div>
      )}

      {/* Missing recommended columns */}
      {result.missing_recommended.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <WarningFilled style={{ color: 'var(--novem-warning)' }} />
            <span>Missing optional columns (defaults will apply)</span>
          </div>
          <div className={styles.tagList}>
            {result.missing_recommended.map((col) => (
              <Tag key={col} color="warning">{col}</Tag>
            ))}
          </div>
        </div>
      )}

      {/* Issues */}
      {result.issues.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <InfoCircleFilled style={{ color: 'var(--novem-accent)' }} />
            <span>
              {errorIssues.length > 0 && <Tag color="error">{errorIssues.length} errors</Tag>}
              {warningIssues.length > 0 && <Tag color="warning">{warningIssues.length} warnings</Tag>}
              {infoIssues.length > 0 && <Tag color="blue">{infoIssues.length} info</Tag>}
            </span>
          </div>
          <div className={styles.issuesList}>
            {result.issues.map((issue, i) => (
              <div key={i} className={styles.issueItem} data-severity={issue.severity}>
                {issue.severity === 'error' && <CloseCircleFilled className={styles.issueIcon} style={{ color: 'var(--novem-error)' }} />}
                {issue.severity === 'warning' && <WarningFilled className={styles.issueIcon} style={{ color: 'var(--novem-warning)' }} />}
                {issue.severity === 'info' && <InfoCircleFilled className={styles.issueIcon} style={{ color: 'var(--novem-accent)' }} />}
                <span className={styles.issueText}>{issue.issue}</span>
                {issue.sample_rows.length > 0 && (
                  <span className={styles.issueSample}>
                    (rows: {issue.sample_rows.join(', ')})
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Clean actions preview */}
      {result.clean_actions_preview.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <CheckCircleFilled style={{ color: 'var(--novem-success)' }} />
            <span>Auto-corrections that will be applied</span>
          </div>
          <div className={styles.actionsList}>
            {result.clean_actions_preview.map((action, i) => (
              <div key={i} className={styles.actionItem}>
                <CheckCircleFilled className={styles.actionIcon} />
                <span>{action}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Currency + status previews */}
      {(result.currency_preview.length > 0 || result.status_preview.length > 0) && (
        <div className={styles.previewRow}>
          {result.currency_preview.length > 0 && (
            <div className={styles.previewChip}>
              <span className={styles.previewChipLabel}>Currencies:</span>
              {result.currency_preview.map((v) => (
                <Tag key={v}>{v}</Tag>
              ))}
            </div>
          )}
          {result.status_preview.length > 0 && (
            <div className={styles.previewChip}>
              <span className={styles.previewChipLabel}>Statuses:</span>
              {result.status_preview.map((v) => (
                <Tag key={v}>{v}</Tag>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Unmapped columns */}
      {result.unmapped_columns.length > 0 && (
        <div className={styles.unmapped}>
          <span className={styles.unmappedLabel}>
            {result.unmapped_columns.length} source column(s) not mapped:
          </span>
          <span className={styles.unmappedList}>
            {result.unmapped_columns.slice(0, 8).join(', ')}
            {result.unmapped_columns.length > 8 && ` +${result.unmapped_columns.length - 8} more`}
          </span>
        </div>
      )}
    </div>
  );
}
