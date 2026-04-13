import { useState, useEffect, useCallback } from 'react';
import { Button } from 'antd';
import {
  DashboardOutlined,
  LineChartOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import TitleBar from '@/components/shell/TitleBar';
import novemLogo from '@/assets/images/novem_logo.png';

// ── Swap these with your real screenshot assets ──
import screen1 from '@/assets/images/screens/screen_01.png';
import screen2 from '@/assets/images/screens/screen_02.png';
import screen3 from '@/assets/images/screens/screen_03.png';
import screen4 from '@/assets/images/screens/screen_04.png';
import screen5 from '@/assets/images/screens/screen_05.png';
import screen6 from '@/assets/images/screens/screen_06.png';
import screen7 from '@/assets/images/screens/screen_07.png';
import screen8 from '@/assets/images/screens/screen_08.png';
import screen9 from '@/assets/images/screens/screen_09.png';
import screen10 from '@/assets/images/screens/screen_10.png';

import { ROUTES } from '@/constants/routes';
import styles from './Landing.module.css';

// ─────────────────────────────────────────────────
// Slide data — update title to match each screenshot
// ─────────────────────────────────────────────────
const SLIDES = [
  { src: screen1, title: 'Dashboard' }, 
  { src: screen2,  title: 'Import Data' },
  { src: screen3,  title: 'Data Viewer' },
  { src: screen4,  title: 'Customers' },
  { src: screen5,  title: 'Products' },
  { src: screen6,  title: 'Insights' },
  { src: screen7,  title: 'Forecasting' },
  { src: screen8,  title: 'Customer Reviews' },
  { src: screen9,  title: 'AI Copilot' },
  { src: screen10,  title: 'Settings — Profile' },
];

const FEATURES = [
  {
    icon: <DashboardOutlined />,
    title: 'Auto-Profiling & KPI Dashboards',
    desc: 'Revenue, AOV, CLV, churn risk — instantly on import.',
  },
  {
    icon: <LineChartOutlined />,
    title: 'ML-Powered Forecasting',
    desc: 'Prophet-based projection with anomaly detection.',
  },
  {
    icon: <RobotOutlined />,
    title: 'AI Copilot',
    desc: 'Plain-English root-cause analysis via local Ollama LLM.',
  },
  {
    icon: <SafetyCertificateOutlined />,
    title: '100% Local & Private',
    desc: 'DuckDB + SQLite. No telemetry. No cloud. Your data stays yours.',
  },
];

/** Auto-advance interval in ms */
const SLIDE_DURATION = 3500;

interface LandingProps {
  theme?: 'dark' | 'light';
}

export default function Landing({ theme = 'dark' }: LandingProps) {
  const navigate = useNavigate();
  const [activeFeature, setActiveFeature] = useState<number | null>(null);
  const [current, setCurrent] = useState(0);
  const [fading, setFading] = useState(false);

  /** Cross-fade to a specific slide index */
  const goTo = useCallback(
    (idx: number) => {
      if (fading || idx === current) return;
      setFading(true);
      setTimeout(() => {
        setCurrent(idx);
        setFading(false);
      }, 280);
    },
    [fading, current],
  );

  // Auto-advance
  useEffect(() => {
    const id = setInterval(() => {
      setCurrent((c) => (c + 1) % SLIDES.length);
    }, SLIDE_DURATION);
    return () => clearInterval(id);
  }, []);

  const handleGetStarted = () => {
    localStorage.setItem('novem-seen-landing', 'true');
    navigate(ROUTES.WELCOME);
  };

  return (
    <div className={styles.landing} data-theme={theme}>
      <TitleBar minimal />

      <div className={styles.body}>

        {/* ══════════ LEFT PANE ══════════ */}
        <div className={styles.left}>

          {/* Logo lockup */}
          <div className={styles.logoLockup}>
            <img src={novemLogo} alt="Novem" className={styles.logo} />
            <div className={styles.logoText}>
              <span className={styles.wordmark}>NOVEM</span>
              <span className={styles.tagline}>E-Commerce Intelligence Platform</span>
            </div>
          </div>

          

          {/* Feature list */}
          <ul className={styles.features}>
            {FEATURES.map((f, i) => (
              <li
                key={i}
                className={`${styles.featureRow} ${activeFeature === i ? styles.featureRowActive : ''}`}
                onMouseEnter={() => setActiveFeature(i)}
                onMouseLeave={() => setActiveFeature(null)}
              >
                <span className={styles.featureIcon}>{f.icon}</span>
                <div className={styles.featureText}>
                  <span className={styles.featureTitle}>{f.title}</span>
                  <span className={styles.featureDesc}>{f.desc}</span>
                </div>
              </li>
            ))}
          </ul>

          {/* CTA */}
          <div className={styles.cta}>
            <Button
              type="primary"
              size="large"
              onClick={handleGetStarted}
              className={styles.ctaBtn}
            >
              Get Started
            </Button>
            <span className={styles.ctaHint}>Set up your workspace in under a minute</span>
          </div>

          {/* Version stamp */}
          <div className={styles.versionStamp}>
            v1.0.0 · 2026
          </div>
        </div>

        {/* ══════════ RIGHT PANE ══════════ */}
        <div className={styles.right}>
          <div className={styles.previewFrame}>
            <div className={styles.previewGlow} />

            {/* Desktop app title bar */}
            <div className={styles.windowBar}>
              <div className={styles.windowDots}>
                <img src={novemLogo} alt="" className={styles.windowAppIcon} />
              </div>

              {/* Slide title in center of title bar */}
              <span className={styles.windowTitle}>
                {SLIDES[current].title} — Novem
              </span>

              {/* Window controls — minimize, maximize, close */}
              <div className={styles.windowPips}>
                <span className={styles.windowControl} aria-label="Minimize">
                  <svg width="10" height="1" viewBox="0 0 10 1"><rect width="10" height="1" /></svg>
                </span>
                <span className={styles.windowControl} aria-label="Maximize">
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><rect x="0.5" y="0.5" width="9" height="9" strokeWidth="1" /></svg>
                </span>
                <span className={`${styles.windowControl} ${styles.windowControlClose}`} aria-label="Close">
                  <svg width="10" height="10" viewBox="0 0 10 10"><path d="M0,0 L10,10 M10,0 L0,10" strokeWidth="1.2" /></svg>
                </span>
              </div>
            </div>

            {/* Carousel viewport — cross-fade between slides */}
            <div className={styles.carouselViewport}>
              {SLIDES.map((slide, i) => (
                <img
                  key={i}
                  src={slide.src}
                  alt={slide.title}
                  className={`${styles.carouselImg} ${i === current ? styles.carouselImgVisible : ''}`}
                  draggable={false}
                />
              ))}

              {/* Gradient fade at bottom — bleeds into frame bg */}
              <div className={styles.previewFade} />

              {/* Thin auto-progress bar at very bottom */}
              <div className={styles.progressTrack}>
                <div
                  className={styles.progressBar}
                  key={current}
                  style={{ animationDuration: `${SLIDE_DURATION}ms` }}
                />
              </div>
            </div>

            {/* Slide pip indicators */}
            <div className={styles.slidePips}>
              {SLIDES.map((_, i) => (
                <button
                  key={i}
                  className={`${styles.pip} ${i === current ? styles.pipActive : ''}`}
                  onClick={() => goTo(i)}
                  aria-label={`View ${SLIDES[i].title}`}
                />
              ))}
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}