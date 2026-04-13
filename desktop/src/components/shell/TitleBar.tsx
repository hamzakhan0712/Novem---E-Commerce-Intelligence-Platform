import {
  ImportOutlined,
  ExportOutlined,
  PoweroffOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  ExpandOutlined,
  BgColorsOutlined,
  SettingOutlined,
  InfoCircleOutlined,
  LockOutlined,
  UserOutlined,
  DashboardOutlined,
  TeamOutlined,
  ShoppingOutlined,
  BulbOutlined,
  LineChartOutlined,
  SmileOutlined,
  RobotOutlined,
  SearchOutlined,
  ShopOutlined,
} from '@ant-design/icons';
import { Avatar, Dropdown, Modal } from 'antd';
import type { MenuProps } from 'antd';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAppStore } from '@/stores/appStore';
import { useAuthStore } from '@/stores/authStore';
import { ROUTES } from '@/constants/routes';
import AlertPanel from '@/components/shared/AlertPanel';
import novemLogo from '@/assets/images/novem_logo.png';

import styles from './TitleBar.module.css';

interface TitleBarProps {
  minimal?: boolean;
}

export default function TitleBar({ minimal = false }: TitleBarProps) {
  const themeMode = useAppStore((s) => s.themeMode);
  const toggleTheme = useAppStore((s) => s.toggleThemeMode);
  const zoomIn = useAppStore((s) => s.zoomIn);
  const zoomOut = useAppStore((s) => s.zoomOut);
  const resetZoom = useAppStore((s) => s.resetZoom);
  const user = useAuthStore((s) => s.user);
  const lock = useAuthStore((s) => s.lock);

  const navigate = useNavigate();

  const [aboutOpen, setAboutOpen] = useState(false);

  const handleMinimize = async () => {
    const { getCurrentWindow } = await import('@tauri-apps/api/window');
    getCurrentWindow().minimize();
  };

  const handleMaximize = async () => {
    const { getCurrentWindow } = await import('@tauri-apps/api/window');
    const win = getCurrentWindow();
    const isMax = await win.isMaximized();
    if (isMax) { win.unmaximize(); } else { win.maximize(); }
  };

  const handleClose = async () => {
    const { getCurrentWindow } = await import('@tauri-apps/api/window');
    getCurrentWindow().close();
  };

  const toggleCommandPalette = useAppStore((s) => s.toggleCommandPalette);

  const fileMenuItems: MenuProps['items'] = [
    {
      key: 'import',
      label: 'Import Data    Ctrl+I',
      icon: <ImportOutlined />,
      onClick: () => navigate(ROUTES.IMPORT),
    },
    {
      key: 'export',
      label: 'Export Report',
      icon: <ExportOutlined />,
      onClick: () => navigate(ROUTES.REPORTS),
    },
    { type: 'divider' },
    {
      key: 'new-store',
      label: 'New Store',
      icon: <ShopOutlined />,
      onClick: () => navigate(ROUTES.STORES),
    },
    { type: 'divider' },
    {
      key: 'settings',
      label: 'Settings    Ctrl+,',
      icon: <SettingOutlined />,
      onClick: () => navigate(ROUTES.SETTINGS),
    },
    {
      key: 'lock',
      label: 'Lock Workspace',
      icon: <LockOutlined />,
      onClick: () => lock(),
    },
    { type: 'divider' },
    {
      key: 'exit',
      label: 'Exit',
      icon: <PoweroffOutlined />,
      onClick: async () => {
        const { getCurrentWindow } = await import('@tauri-apps/api/window');
        getCurrentWindow().close();
      },
    },
  ];

  const viewMenuItems: MenuProps['items'] = [
    {
      key: 'command-palette',
      label: 'Command Palette    Ctrl+K',
      icon: <SearchOutlined />,
      onClick: () => toggleCommandPalette(),
    },
    { type: 'divider' },
    {
      key: 'nav-group',
      type: 'group',
      label: 'Navigate',
      children: [
        { key: 'nav-dashboard', label: 'Dashboard', icon: <DashboardOutlined />, onClick: () => navigate(ROUTES.DASHBOARD) },
        { key: 'nav-customers', label: 'Customers', icon: <TeamOutlined />, onClick: () => navigate(ROUTES.CUSTOMERS) },
        { key: 'nav-products', label: 'Products', icon: <ShoppingOutlined />, onClick: () => navigate(ROUTES.PRODUCTS) },
        { key: 'nav-insights', label: 'Insights', icon: <BulbOutlined />, onClick: () => navigate(ROUTES.INSIGHTS) },
        { key: 'nav-forecasting', label: 'Forecasting', icon: <LineChartOutlined />, onClick: () => navigate(ROUTES.FORECASTING) },
        { key: 'nav-sentiment', label: 'Reviews', icon: <SmileOutlined />, onClick: () => navigate(ROUTES.SENTIMENT) },
        { key: 'nav-copilot', label: 'AI Copilot', icon: <RobotOutlined />, onClick: () => navigate(ROUTES.COPILOT) },
      ],
    },
    { type: 'divider' },
    {
      key: 'zoom-in',
      label: 'Zoom In    Ctrl++',
      icon: <ZoomInOutlined />,
      onClick: zoomIn,
    },
    {
      key: 'zoom-out',
      label: 'Zoom Out    Ctrl+-',
      icon: <ZoomOutOutlined />,
      onClick: zoomOut,
    },
    {
      key: 'reset-zoom',
      label: 'Reset Zoom    Ctrl+0',
      icon: <ExpandOutlined />,
      onClick: resetZoom,
    },
    { type: 'divider' },
    {
      key: 'toggle-theme',
      label: `${themeMode === 'dark' ? 'Light' : 'Dark'} Mode`,
      icon: <BgColorsOutlined />,
      onClick: toggleTheme,
    },
  ];

  const helpMenuItems: MenuProps['items'] = [
    {
      key: 'about',
      label: 'About NOVEM',
      icon: <InfoCircleOutlined />,
      onClick: () => setAboutOpen(true),
    },
  ];

  return (
    <div className={styles.titleBar}>
      <div className={styles.logo}>
        <img src={novemLogo} alt="NOVEM" className={styles.logoImg} />
        <span className={styles.logoText}>NOVEM</span>
      </div>

      {!minimal && (
        <div id="tour-titlebar-menus" className={styles.menuBar}>
          <Dropdown menu={{ items: fileMenuItems }} trigger={['click']}>
            <span className={styles.menuItem}>File</span>
          </Dropdown>
          <Dropdown menu={{ items: viewMenuItems }} trigger={['click']}>
            <span className={styles.menuItem}>View</span>
          </Dropdown>
          <Dropdown menu={{ items: helpMenuItems }} trigger={['click']}>
            <span className={styles.menuItem}>Help</span>
          </Dropdown>
        </div>
      )}

      <div className={styles.dragRegion} />

      {!minimal && user && (
        <div className={styles.profileArea}>
          <span id="tour-notifications"><AlertPanel /></span>
          <Dropdown
            menu={{
              items: [
                {
                  key: 'profile-header',
                  type: 'group',
                  label: (
                    <div className={styles.profileHeader}>
                      <Avatar
                        size={32}
                        src={user.avatar_photo || (user.avatar_seed ? `https://api.dicebear.com/7.x/adventurer/svg?seed=${user.avatar_seed}` : undefined)}
                        icon={!user.avatar_photo && !user.avatar_seed ? <UserOutlined /> : undefined}
                      />
                      <div className={styles.profileDetails}>
                        <span className={styles.profileName}>{user.name}</span>
                        {user.email && <span className={styles.profileEmail}>{user.email}</span>}
                      </div>
                    </div>
                  ),
                },
                { type: 'divider' },
                {
                  key: 'settings',
                  label: 'Profile & Settings',
                  icon: <SettingOutlined />,
                  onClick: () => navigate(ROUTES.SETTINGS),
                },
                {
                  key: 'lock',
                  label: 'Lock',
                  icon: <LockOutlined />,
                  onClick: () => lock(),
                },
              ] satisfies MenuProps['items'],
            }}
            trigger={['click']}
            placement="bottomRight"
          >
            <button id="tour-profile" className={styles.profileBtn}>
              <Avatar
                size={22}
                src={user.avatar_photo || (user.avatar_seed ? `https://api.dicebear.com/7.x/adventurer/svg?seed=${user.avatar_seed}` : undefined)}
                icon={!user.avatar_photo && !user.avatar_seed ? <UserOutlined /> : undefined}
                style={{ cursor: 'pointer' }}
              />
            </button>
          </Dropdown>
        </div>
      )}

      <div className={styles.windowControls}>
        <button className={styles.winBtn} onClick={handleMinimize} title="Minimize">
          <svg width="10" height="1" viewBox="0 0 10 1" fill="currentColor">
            <rect width="10" height="1" />
          </svg>
        </button>
        <button className={styles.winBtn} onClick={handleMaximize} title="Maximize">
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1">
            <rect x="0.5" y="0.5" width="9" height="9" rx="1.5" />
          </svg>
        </button>
        <button className={`${styles.winBtn} ${styles.winBtnClose}`} onClick={handleClose} title="Close">
          <svg width="10" height="10" viewBox="0 0 10 10" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round">
            <line x1="1" y1="1" x2="9" y2="9" />
            <line x1="9" y1="1" x2="1" y2="9" />
          </svg>
        </button>
      </div>

      <Modal
        title={null}
        open={aboutOpen}
        onCancel={() => setAboutOpen(false)}
        footer={null}
        width={720}
        centered
      >
        <div style={{ padding: '24px 16px 12px' }}>
          {/* Header */}
          <div style={{ textAlign: 'center', marginBottom: 28 }}>
            <img src={novemLogo} alt="NOVEM" style={{ width: 64, height: 64, marginBottom: 12, filter: 'drop-shadow(0 4px 16px rgba(82, 196, 26, 0.15))' }} />
            <h2 style={{ margin: '0 0 4px', fontSize: 26, fontWeight: 700, letterSpacing: 4 }}>NOVEM</h2>
            <p style={{ margin: '0 0 2px', color: 'var(--novem-text-secondary)', fontSize: 14, letterSpacing: 0.5 }}>
              E-Commerce Intelligence Platform
            </p>
            <p style={{ margin: 0, fontSize: 12, color: 'var(--novem-text-tertiary)' }}>
              Version 0.3.0 · Desktop Edition
            </p>
          </div>

          {/* Purpose */}
          <div style={{ background: 'var(--novem-bg-secondary)', borderRadius: 10, padding: '16px 20px', marginBottom: 20 }}>
            <h4 style={{ margin: '0 0 8px', fontSize: 13, fontWeight: 600, color: 'var(--novem-accent)', letterSpacing: 0.5, textTransform: 'uppercase' }}>Purpose</h4>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--novem-text-secondary)', lineHeight: 1.75 }}>
              NOVEM brings enterprise-grade data science to small and medium e-commerce businesses.
              It provides automated profiling, smart KPI dashboards, ML-powered forecasting, anomaly
              detection, and AI-generated insights — all running locally on your machine with zero
              subscriptions and complete data privacy.
            </p>
          </div>

          {/* Features */}
          <div style={{ marginBottom: 20 }}>
            <h4 style={{ margin: '0 0 12px', fontSize: 13, fontWeight: 600, color: 'var(--novem-accent)', letterSpacing: 0.5, textTransform: 'uppercase' }}>Features</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 24px' }}>
              {[
                ['📊', 'Real-Time Dashboard', 'KPIs, health score, and business metrics at a glance'],
                ['👥', 'Customer Intelligence', 'RFM segmentation, CLV prediction, and churn analysis'],
                ['📦', 'Product Analytics', 'Performance tracking, ABC classification, and basket analysis'],
                ['🔮', 'Demand Forecasting', 'Prophet-powered sales and revenue predictions'],
                ['💡', 'Automated Insights', 'AI-generated root cause analysis and recommendations'],
                ['😊', 'Sentiment Analysis', 'NLP-powered review analysis and brand perception'],
                ['🤖', 'AI Copilot', 'Natural language queries with local LLM via Ollama'],
                ['📈', 'Marketing ROI', 'Ad spend optimization and channel performance'],
                ['🔔', 'Smart Alerts', 'Anomaly detection and proactive notifications'],
                ['📄', 'Report Generation', 'Branded PDF reports for CEOs and technical teams'],
              ].map(([icon, title, desc]) => (
                <div key={title} style={{ display: 'flex', gap: 10, padding: '6px 0' }}>
                  <span style={{ fontSize: 18, flexShrink: 0, lineHeight: '24px' }}>{icon}</span>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--novem-text-primary)', lineHeight: '20px' }}>{title}</div>
                    <div style={{ fontSize: 11, color: 'var(--novem-text-tertiary)', lineHeight: '16px' }}>{desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Thought Process */}
          <div style={{ background: 'var(--novem-bg-secondary)', borderRadius: 10, padding: '16px 20px', marginBottom: 20 }}>
            <h4 style={{ margin: '0 0 8px', fontSize: 13, fontWeight: 600, color: 'var(--novem-accent)', letterSpacing: 0.5, textTransform: 'uppercase' }}>Built With Intent</h4>
            <p style={{ margin: '0 0 8px', fontSize: 13, color: 'var(--novem-text-secondary)', lineHeight: 1.75 }}>
              Most analytics tools are cloud-only SaaS products with expensive subscriptions and data
              privacy concerns. NOVEM takes a different approach — a local-first desktop application
              where your data never leaves your machine.
            </p>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--novem-text-secondary)', lineHeight: 1.75 }}>
              By combining a modern React interface with a Python analytics engine powered by DuckDB,
              scikit-learn, and Prophet, NOVEM delivers the same capabilities as cloud platforms —
              without the cost, complexity, or compromise on privacy.
            </p>
          </div>

          {/* Tech Stack */}
          <div style={{ display: 'flex', justifyContent: 'center', gap: 6, flexWrap: 'wrap', marginBottom: 20 }}>
            {['React', 'TypeScript', 'Tauri v2', 'FastAPI', 'DuckDB', 'Python 3.12', 'scikit-learn', 'Prophet', 'Ollama'].map((tech) => (
              <span key={tech} style={{
                fontSize: 10,
                fontWeight: 600,
                padding: '3px 10px',
                borderRadius: 4,
                background: 'var(--novem-bg-hover)',
                color: 'var(--novem-text-tertiary)',
                letterSpacing: 0.3,
              }}>
                {tech}
              </span>
            ))}
          </div>

          {/* Footer */}
          <div style={{ borderTop: '1px solid var(--novem-border-default)', paddingTop: 12, textAlign: 'center' }}>
            <p style={{ margin: 0, fontSize: 10, color: 'var(--novem-text-tertiary)', opacity: 0.7 }}>
              © {new Date().getFullYear()} NOVEM · Local-first, privacy-by-design
            </p>
          </div>
        </div>
      </Modal>
    </div>
  );
}
