import { useState, useMemo } from 'react';

import {
  CheckCircleFilled,
  CloseOutlined,
  DashboardOutlined,
  ImportOutlined,
  LineChartOutlined,
  RobotOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { Button, Progress } from 'antd';
import { useNavigate } from 'react-router-dom';

import { ROUTES } from '@/constants/routes';
import { useDataAvailabilityStore } from '@/stores/dataAvailabilityStore';

import styles from './GettingStartedChecklist.module.css';

const DISMISSED_KEY = 'novem-getting-started-dismissed';
const VISITED_KEY = 'novem-visited-pages';

interface ChecklistItem {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  route: string;
  check: (visited: Set<string>, hasData: boolean) => boolean;
}

const CHECKLIST_ITEMS: ChecklistItem[] = [
  {
    id: 'import',
    label: 'Import your data',
    description: 'Upload a CSV, connect Google Sheets, or load sample data to get started.',
    icon: <ImportOutlined />,
    route: ROUTES.IMPORT,
    check: (_visited, hasData) => hasData,
  },
  {
    id: 'dashboard',
    label: 'Explore the Dashboard',
    description: 'View your KPIs, revenue trends, and top products.',
    icon: <DashboardOutlined />,
    route: ROUTES.DASHBOARD,
    check: (visited, hasData) => hasData && visited.has('dashboard'),
  },
  {
    id: 'customers',
    label: 'Check Customer Segments',
    description: 'See customer lifetime value, churn risk, and RFM segments.',
    icon: <TeamOutlined />,
    route: ROUTES.CUSTOMERS,
    check: (visited) => visited.has('customers'),
  },
  {
    id: 'forecasting',
    label: 'Run a Forecast',
    description: 'Generate AI-powered sales predictions with anomaly detection.',
    icon: <LineChartOutlined />,
    route: ROUTES.FORECASTING,
    check: (visited) => visited.has('forecasting'),
  },
  {
    id: 'copilot',
    label: 'Ask the AI Copilot',
    description: 'Ask a plain-English question like "Why did revenue drop last month?"',
    icon: <RobotOutlined />,
    route: ROUTES.COPILOT,
    check: (visited) => visited.has('copilot'),
  },
];

function getVisitedPages(): Set<string> {
  try {
    const raw = localStorage.getItem(VISITED_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

export function markPageVisited(pageKey: string) {
  const visited = getVisitedPages();
  if (visited.has(pageKey)) return;
  visited.add(pageKey);
  localStorage.setItem(VISITED_KEY, JSON.stringify([...visited]));
}

export default function GettingStartedChecklist() {
  const navigate = useNavigate();
  const hasAnyData = useDataAvailabilityStore((s) => s.hasAnyData);
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem(DISMISSED_KEY) === 'true',
  );
  const [visited] = useState(() => getVisitedPages());

  const dataAvailable = hasAnyData();

  const completedItems = useMemo(
    () => CHECKLIST_ITEMS.filter((item) => item.check(visited, dataAvailable)),
    [visited, dataAvailable],
  );

  const completedCount = completedItems.length;
  const totalCount = CHECKLIST_ITEMS.length;
  const allDone = completedCount === totalCount;
  const percent = Math.round((completedCount / totalCount) * 100);

  if (dismissed) return null;

  const handleDismiss = () => {
    localStorage.setItem(DISMISSED_KEY, 'true');
    setDismissed(true);
  };

  return (
    <div className={styles.checklist}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h3 className={styles.title}>
            {allDone ? 'All set! You\'re ready to go.' : 'Getting Started'}
          </h3>
          <span className={styles.progress}>
            {completedCount} of {totalCount} completed
          </span>
        </div>
        <div className={styles.headerRight}>
          <Progress
            type="circle"
            percent={percent}
            size={36}
            strokeWidth={10}
            strokeColor="var(--novem-accent)"
          />
          <Button
            type="text"
            size="small"
            icon={<CloseOutlined />}
            onClick={handleDismiss}
            className={styles.dismissBtn}
          />
        </div>
      </div>

      <div className={styles.items}>
        {CHECKLIST_ITEMS.map((item) => {
          const done = item.check(visited, dataAvailable);
          return (
            <button
              key={item.id}
              className={`${styles.item} ${done ? styles.itemDone : ''}`}
              onClick={() => navigate(item.route)}
            >
              <span className={styles.itemIcon}>
                {done ? (
                  <CheckCircleFilled className={styles.checkIcon} />
                ) : (
                  item.icon
                )}
              </span>
              <div className={styles.itemText}>
                <span className={styles.itemLabel}>{item.label}</span>
                <span className={styles.itemDesc}>{item.description}</span>
              </div>
            </button>
          );
        })}
      </div>

      {allDone && (
        <div className={styles.footer}>
          <Button type="primary" size="small" onClick={handleDismiss}>
            Dismiss checklist
          </Button>
        </div>
      )}
    </div>
  );
}
