import { Progress, Tooltip } from 'antd';
import {
  SafetyCertificateOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';

import { useDataQuality } from '@/hooks/useDataQuality';

import styles from './DataQualityCard.module.css';

const GRADE_COLORS: Record<string, string> = {
  A: '#52c41a',
  B: '#73d13d',
  C: '#faad14',
  D: '#ff7a45',
  F: '#ff4d4f',
};

function gradeIcon(grade: string) {
  if (grade === 'A' || grade === 'B') return <CheckCircleOutlined />;
  if (grade === 'C') return <WarningOutlined />;
  return <CloseCircleOutlined />;
}

interface ComponentBarProps {
  label: string;
  score: number;
  detail: string;
}

function ComponentBar({ label, score, detail }: ComponentBarProps) {
  const color = score >= 80 ? '#52c41a' : score >= 60 ? '#faad14' : '#ff4d4f';
  return (
    <Tooltip title={detail}>
      <div className={styles.componentRow}>
        <span className={styles.componentLabel}>{label}</span>
        <Progress
          percent={score}
          size="small"
          strokeColor={color}
          showInfo={false}
          className={styles.componentBar}
        />
        <span className={styles.componentScore}>{score}%</span>
      </div>
    </Tooltip>
  );
}

export default function DataQualityCard() {
  const { quality, loading } = useDataQuality();

  if (loading || !quality) {
    return null;
  }

  const { overall_score, grade, components } = quality;
  const gradeColor = GRADE_COLORS[grade] ?? '#8c8c8c';

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <SafetyCertificateOutlined className={styles.headerIcon} />
        <span className={styles.headerTitle}>Data Quality</span>
        <Tooltip title={`Grade ${grade} — ${overall_score}% overall`}>
          <span className={styles.grade} style={{ color: gradeColor }}>
            {gradeIcon(grade)} {grade}
          </span>
        </Tooltip>
      </div>

      <div className={styles.scoreRow}>
        <Progress
          type="circle"
          percent={overall_score}
          size={64}
          strokeColor={gradeColor}
          format={(pct) => `${pct}`}
        />
        <div className={styles.components}>
          <ComponentBar label="Import Health" score={components.import_health.score} detail={components.import_health.detail} />
          <ComponentBar label="Completeness" score={components.completeness.score} detail={components.completeness.detail} />
          <ComponentBar label="Freshness" score={components.freshness.score} detail={components.freshness.detail} />
          <ComponentBar label="Volume" score={components.volume.score} detail={components.volume.detail} />
        </div>
      </div>

      {quality.components.completeness.issues.length > 0 && (
        <div className={styles.issues}>
          {quality.components.completeness.issues.slice(0, 3).map((issue, i) => (
            <span key={i} className={styles.issue}>
              <WarningOutlined /> {issue}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
