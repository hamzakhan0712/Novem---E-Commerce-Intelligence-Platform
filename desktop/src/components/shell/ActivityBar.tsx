import {
  BulbOutlined,
  DatabaseOutlined,
  DashboardOutlined,
  FileTextOutlined,
  FundOutlined,
  ImportOutlined,
  LineChartOutlined,
  RobotOutlined,
  SettingOutlined,
  ShopOutlined,
  ShoppingOutlined,
  SmileOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { Tooltip } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';

import { ROUTES } from '@/constants/routes';
import { useDataAvailabilityStore } from '@/stores/dataAvailabilityStore';

import styles from './ActivityBar.module.css';

const NAV_ITEMS = [
  { key: 'dashboard', icon: <DashboardOutlined />, label: 'Dashboard', route: ROUTES.DASHBOARD },
  { key: 'import', icon: <ImportOutlined />, label: 'Import Data', route: ROUTES.IMPORT },
  { key: 'data-viewer', icon: <DatabaseOutlined />, label: 'Data Viewer', route: ROUTES.DATA_VIEWER },
  { key: 'customers', icon: <TeamOutlined />, label: 'Customers', route: ROUTES.CUSTOMERS },
  { key: 'products', icon: <ShoppingOutlined />, label: 'Products', route: ROUTES.PRODUCTS },
  { key: 'marketing', icon: <FundOutlined />, label: 'Marketing', route: ROUTES.MARKETING },
  { key: 'insights', icon: <BulbOutlined />, label: 'Insights', route: ROUTES.INSIGHTS },
  { key: 'forecasting', icon: <LineChartOutlined />, label: 'Forecasting', route: ROUTES.FORECASTING },
  { key: 'sentiment', icon: <SmileOutlined />, label: 'Reviews', route: ROUTES.SENTIMENT },
  { key: 'copilot', icon: <RobotOutlined />, label: 'AI Copilot', route: ROUTES.COPILOT },
  { key: 'reports', icon: <FileTextOutlined />, label: 'Reports', route: ROUTES.REPORTS },
];

const BOTTOM_ITEMS = [
  { key: 'stores', icon: <ShopOutlined />, label: 'Stores', route: ROUTES.STORES },
  { key: 'settings', icon: <SettingOutlined />, label: 'Settings', route: ROUTES.SETTINGS },
];

const ALWAYS_ACCESSIBLE = new Set(['import']);

export default function ActivityBar() {
  const navigate = useNavigate();
  const location = useLocation();
  const isPageAccessible = useDataAvailabilityStore((s) => s.isPageAccessible);
  const loaded = useDataAvailabilityStore((s) => s.loaded);

  const isActive = (route: string) => location.pathname === route;

  const isDisabled = (key: string) => {
    if (ALWAYS_ACCESSIBLE.has(key)) return false;
    if (!loaded) return false;
    return !isPageAccessible(key);
  };

  const handleNavClick = (route: string, key?: string) => {
    if (key && isDisabled(key)) return;
    navigate(route);
  };

  return (
    <nav className={styles.activityBar}>
      <div className={styles.topIcons}>
        {NAV_ITEMS.map((item) => {
          const disabled = isDisabled(item.key);
          return (
            <Tooltip key={item.key} title={disabled ? `${item.label} (no data)` : item.label} placement="right">
              <button
                className={`${styles.navItem} ${isActive(item.route) ? styles.navItemActive : ''} ${disabled ? styles.navItemDisabled : ''}`}
                onClick={() => handleNavClick(item.route, item.key)}
              >
                {item.icon}
              </button>
            </Tooltip>
          );
        })}
      </div>
      <div className={styles.bottomIcons}>
        {BOTTOM_ITEMS.map((item) => (
          <Tooltip key={item.key} title={item.label} placement="right">
            <button
              className={`${styles.navItem} ${isActive(item.route) ? styles.navItemActive : ''}`}
              onClick={() => handleNavClick(item.route)}
            >
              {item.icon}
            </button>
          </Tooltip>
        ))}
      </div>
    </nav>
  );
}
