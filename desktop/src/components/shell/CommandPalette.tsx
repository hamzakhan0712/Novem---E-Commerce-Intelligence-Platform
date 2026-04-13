import { useState, useEffect, useRef, useMemo } from 'react';

import {
  SearchOutlined,
  SettingOutlined,
  ImportOutlined,
  DashboardOutlined,
  TeamOutlined,
  ShoppingOutlined,
  BgColorsOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import { useAppStore } from '@/stores/appStore';
import { ROUTES } from '@/constants/routes';

import styles from './CommandPalette.module.css';

interface Command {
  id: string;
  label: string;
  group: string;
  shortcut?: string;
  icon: React.ReactNode;
  action: () => void;
}

export default function CommandPalette() {
  const isOpen = useAppStore((s) => s.commandPaletteOpen);
  const close = useAppStore((s) => s.setCommandPaletteOpen);
  const toggleTheme = useAppStore((s) => s.toggleThemeMode);
  const zoomIn = useAppStore((s) => s.zoomIn);
  const zoomOut = useAppStore((s) => s.zoomOut);
  const resetZoom = useAppStore((s) => s.resetZoom);
  const navigate = useNavigate();

  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const nav = (route: string) => {
    navigate(route);
    close(false);
  };

  const commands: Command[] = useMemo(
    () => [
      { id: 'nav-dashboard', label: 'Go to Dashboard', group: 'Navigation', icon: <DashboardOutlined />, action: () => nav(ROUTES.DASHBOARD) },
      { id: 'nav-customers', label: 'Go to Customers', group: 'Navigation', icon: <TeamOutlined />, action: () => nav(ROUTES.CUSTOMERS) },
      { id: 'nav-products', label: 'Go to Products', group: 'Navigation', icon: <ShoppingOutlined />, action: () => nav(ROUTES.PRODUCTS) },
      { id: 'nav-import', label: 'Import Data', group: 'Navigation', shortcut: 'Ctrl+I', icon: <ImportOutlined />, action: () => nav(ROUTES.IMPORT) },
      { id: 'nav-settings', label: 'Go to Settings', group: 'Navigation', shortcut: 'Ctrl+,', icon: <SettingOutlined />, action: () => nav(ROUTES.SETTINGS) },
      { id: 'toggle-theme', label: 'Toggle Dark / Light Mode', group: 'Appearance', icon: <BgColorsOutlined />, action: () => { toggleTheme(); close(false); } },
      { id: 'zoom-in', label: 'Zoom In', group: 'Appearance', shortcut: 'Ctrl++', icon: <SearchOutlined />, action: () => { zoomIn(); close(false); } },
      { id: 'zoom-out', label: 'Zoom Out', group: 'Appearance', shortcut: 'Ctrl+-', icon: <SearchOutlined />, action: () => { zoomOut(); close(false); } },
      { id: 'zoom-reset', label: 'Reset Zoom', group: 'Appearance', shortcut: 'Ctrl+0', icon: <SearchOutlined />, action: () => { resetZoom(); close(false); } },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const filtered = useMemo(() => {
    if (!query.trim()) return commands;
    const q = query.toLowerCase();
    return commands.filter(
      (c) => c.label.toLowerCase().includes(q) || c.group.toLowerCase().includes(q),
    );
  }, [query, commands]);

  const groups = useMemo(() => {
    const map = new Map<string, Command[]>();
    for (const cmd of filtered) {
      const arr = map.get(cmd.group) ?? [];
      arr.push(cmd);
      map.set(cmd.group, arr);
    }
    return map;
  }, [filtered]);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setActiveIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      close(false);
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    }
    if (e.key === 'Enter' && filtered[activeIndex]) {
      filtered[activeIndex].action();
    }
  };

  if (!isOpen) return null;

  let flatIndex = 0;

  return (
    <div className={styles.overlay} onClick={() => close(false)}>
      <div className={styles.palette} onClick={(e) => e.stopPropagation()} onKeyDown={handleKeyDown}>
        <div className={styles.inputWrapper}>
          <SearchOutlined className={styles.searchIcon} />
          <input
            ref={inputRef}
            className={styles.input}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command…"
          />
        </div>
        <div className={styles.results}>
          {filtered.length === 0 && (
            <div className={styles.empty}>No matching commands</div>
          )}
          {Array.from(groups.entries()).map(([group, cmds]) => (
            <div key={group}>
              <div className={styles.groupLabel}>{group}</div>
              {cmds.map((cmd) => {
                const idx = flatIndex++;
                return (
                  <div
                    key={cmd.id}
                    className={`${styles.item} ${idx === activeIndex ? styles.itemActive : ''}`}
                    onClick={cmd.action}
                    onMouseEnter={() => setActiveIndex(idx)}
                  >
                    <span className={styles.itemIcon}>{cmd.icon}</span>
                    <span className={styles.itemLabel}>{cmd.label}</span>
                    {cmd.shortcut && (
                      <span className={styles.itemShortcut}>{cmd.shortcut}</span>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
