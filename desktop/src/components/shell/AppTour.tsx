import { useState, useEffect, useRef } from 'react';

import { Tour } from 'antd';
import type { TourProps } from 'antd';

import screen01 from '@/assets/images/screens/screen_01.png';
import screen02 from '@/assets/images/screens/screen_02.png';
import screen04 from '@/assets/images/screens/screen_04.png';
import screen05 from '@/assets/images/screens/screen_05.png';
import screen06 from '@/assets/images/screens/screen_06.png';
import screen07 from '@/assets/images/screens/screen_07.png';
import screen09 from '@/assets/images/screens/screen_09.png';
import screen10 from '@/assets/images/screens/screen_10.png';

const TOUR_SEEN_KEY = 'novem-tour-completed';

function getNavButton(index: number): HTMLElement | null {
  const buttons = document.querySelectorAll('nav button');
  return (buttons[index] as HTMLElement) ?? null;
}

function getById(id: string): HTMLElement | null {
  return document.getElementById(id);
}

type TourTarget = HTMLElement | (() => HTMLElement) | (() => null) | null | undefined;

function tourTarget(fn: () => HTMLElement | null): TourTarget {
  return fn as TourTarget;
}

function TourCover({ src, alt }: { src: string; alt: string }) {
  return (
    <div style={{
      position: 'relative',
      width: '100%',
      height: 180,
      borderRadius: '8px 8px 0 0',
      overflow: 'hidden',
    }}>
      <img
        src={src}
        alt={alt}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          objectPosition: 'top center',
          display: 'block',
        }}
      />
      <div style={{
        position: 'absolute',
        inset: 0,
        background: 'linear-gradient(to bottom, transparent 30%, rgba(0,0,0,0.75) 100%)',
        pointerEvents: 'none',
      }} />
    </div>
  );
}

export default function AppTour() {
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState(0);
  const stepsRef = useRef<TourProps['steps']>([]);

  useEffect(() => {
    const seen = localStorage.getItem(TOUR_SEEN_KEY);
    if (seen) return;

    const timer = setTimeout(() => setOpen(true), 800);
    return () => clearTimeout(timer);
  }, []);

  const handleClose = () => {
    setOpen(false);
    setCurrent(0);
    localStorage.setItem(TOUR_SEEN_KEY, 'true');
  };

  stepsRef.current = [
    // ── Shell: Title bar menus ─────────────────────────────────────
    {
      title: 'Menu Bar',
      description: 'Access key actions from File, View, and Help menus — import data, export reports, navigate pages, manage zoom, toggle theme, lock your workspace, and more.',
      target: tourTarget(() => getById('tour-titlebar-menus')),
      placement: 'bottomLeft',
    },
    // ── Shell: Notifications ───────────────────────────────────────
    {
      title: 'Notifications',
      description: 'Real-time alerts and sync activity for your store — unusual spikes, stockout warnings, import completions, and system notifications all appear here.',
      target: tourTarget(() => getById('tour-notifications')),
      placement: 'bottomRight',
    },
    // ── Shell: Profile ─────────────────────────────────────────────
    {
      title: 'Profile',
      description: 'Quick access to your profile, settings, and workspace lock. Click your avatar to manage your account.',
      target: tourTarget(() => getById('tour-profile')),
      placement: 'bottomRight',
    },
    // ── Navigation: Dashboard ──────────────────────────────────────
    {
      title: 'Dashboard',
      description: 'Your command center — KPI cards, revenue trends, customer health scores, and order metrics update automatically when you import data.',
      cover: <TourCover src={screen01} alt="Dashboard" />,
      target: tourTarget(() => getNavButton(0)),
      placement: 'right',
    },
    // ── Navigation: Import ─────────────────────────────────────────
    {
      title: 'Import Data',
      description: 'Bring in your store data from CSV files, Google Sheets, or connect directly to Shopify. NOVEM auto-profiles your data and builds analytics instantly.',
      cover: <TourCover src={screen02} alt="Import Data" />,
      target: tourTarget(() => getNavButton(1)),
      placement: 'right',
    },
    // ── Navigation: Customers ──────────────────────────────────────
    {
      title: 'Customers',
      description: 'Deep customer analytics — segmentation, lifetime value scoring, repeat purchase timelines, and at-risk customer identification.',
      cover: <TourCover src={screen04} alt="Customers" />,
      target: tourTarget(() => getNavButton(3)),
      placement: 'right',
    },
    // ── Navigation: Products ───────────────────────────────────────
    {
      title: 'Products',
      description: 'Product performance rankings, frequently bought together analysis, and inventory insights to optimize your catalog.',
      cover: <TourCover src={screen05} alt="Products" />,
      target: tourTarget(() => getNavButton(4)),
      placement: 'right',
    },
    // ── Navigation: Insights ───────────────────────────────────────
    {
      title: 'Insights',
      description: 'Your store\'s DNA — business health radar, smart recommendations, and auto-generated plain-language insights about your data.',
      cover: <TourCover src={screen06} alt="Insights" />,
      target: tourTarget(() => getNavButton(5)),
      placement: 'right',
    },
    // ── Navigation: Forecasting ────────────────────────────────────
    {
      title: 'Forecasting',
      description: 'AI-powered sales predictions using Prophet and scikit-learn. Forecast revenue, detect unusual activity, and plan ahead with confidence.',
      cover: <TourCover src={screen07} alt="Forecasting" />,
      target: tourTarget(() => getNavButton(6)),
      placement: 'right',
    },
    // ── Navigation: AI Copilot ─────────────────────────────────────
    {
      title: 'AI Copilot',
      description: 'Ask questions in plain English — "Why did revenue drop last month?" — and get instant analysis powered by a local LLM via Ollama.',
      cover: <TourCover src={screen09} alt="AI Copilot" />,
      target: tourTarget(() => getNavButton(8)),
      placement: 'right',
    },
    // ── Navigation: Settings ───────────────────────────────────────
    {
      title: 'Settings',
      description: 'Manage your profile, store connections, preferences, security, and notification settings — all in one place.',
      cover: <TourCover src={screen10} alt="Settings" />,
      target: tourTarget(() => getNavButton(11)),
      placement: 'right',
    },
    // ── Shell: Engine status & store name ──────────────────────────
    {
      title: 'Engine Status & Store',
      description: 'Monitor the compute engine connection in real-time. The green dot means the analytics engine is running. Your active store name is displayed alongside it.',
      target: tourTarget(() => getById('tour-engine-status')),
      placement: 'topLeft',
    },
    // ── Shell: Zoom controls ───────────────────────────────────────
    {
      title: 'Zoom Controls',
      description: 'Adjust the interface zoom level to your comfort. Use the +/− buttons here or the keyboard shortcuts Ctrl++ and Ctrl+−.',
      target: tourTarget(() => getById('tour-zoom-controls')),
      placement: 'topRight',
    },
    // ── Shell: Theme toggle ────────────────────────────────────────
    {
      title: 'Theme Toggle',
      description: 'Switch between Light and Dark mode instantly. Your preference is remembered across sessions.',
      target: tourTarget(() => getById('tour-theme-toggle')),
      placement: 'topRight',
    },
  ];

  return (
    <Tour
      open={open}
      current={current}
      onChange={setCurrent}
      onClose={handleClose}
      steps={stepsRef.current}
      type="primary"
    />
  );
}
