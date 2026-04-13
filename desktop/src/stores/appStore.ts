import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type ThemeMode = 'dark' | 'light';

const THEME_KEY = 'novem-theme';

function readTheme(): ThemeMode {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === 'light' || stored === 'dark') return stored;
  localStorage.setItem(THEME_KEY, 'dark');
  return 'dark';
}

interface BackgroundTask {
  id: string;
  label: string;
  progress: number; // 0-100
}

interface AppState {
  themeMode: ThemeMode;
  engineStatus: 'connecting' | 'connected' | 'disconnected';
  activeModule: string;
  commandPaletteOpen: boolean;
  zoomLevel: number;
  backgroundTasks: BackgroundTask[];

  setThemeMode: (mode: ThemeMode) => void;
  toggleThemeMode: () => void;
  setEngineStatus: (status: AppState['engineStatus']) => void;
  setActiveModule: (module: string) => void;
  toggleCommandPalette: () => void;
  setCommandPaletteOpen: (open: boolean) => void;
  setZoomLevel: (level: number) => void;
  zoomIn: () => void;
  zoomOut: () => void;
  resetZoom: () => void;
  addBackgroundTask: (id: string, label: string) => void;
  updateBackgroundTask: (id: string, progress: number) => void;
  removeBackgroundTask: (id: string) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      themeMode: readTheme(),
      engineStatus: 'connecting',
      activeModule: 'dashboard',
      commandPaletteOpen: false,
      zoomLevel: 100,
      backgroundTasks: [],

      setThemeMode: (mode) => {
        document.documentElement.setAttribute('data-theme', mode);
        localStorage.setItem(THEME_KEY, mode);
        set({ themeMode: mode });
      },
      toggleThemeMode: () =>
        set((state) => {
          const next = state.themeMode === 'dark' ? 'light' : 'dark';
          document.documentElement.setAttribute('data-theme', next);
          localStorage.setItem(THEME_KEY, next);
          return { themeMode: next };
        }),
      setEngineStatus: (status) => set({ engineStatus: status }),
      setActiveModule: (module) => set({ activeModule: module }),
      toggleCommandPalette: () => set((s) => ({ commandPaletteOpen: !s.commandPaletteOpen })),
      setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
      setZoomLevel: (level) => {
        const clamped = Math.min(150, Math.max(80, level));
        document.documentElement.style.setProperty('--app-zoom', String(clamped / 100));
        set({ zoomLevel: clamped });
      },
      zoomIn: () =>
        set((s) => {
          const next = Math.min(150, s.zoomLevel + 10);
          document.documentElement.style.setProperty('--app-zoom', String(next / 100));
          return { zoomLevel: next };
        }),
      zoomOut: () =>
        set((s) => {
          const next = Math.max(80, s.zoomLevel - 10);
          document.documentElement.style.setProperty('--app-zoom', String(next / 100));
          return { zoomLevel: next };
        }),
      resetZoom: () => {
        document.documentElement.style.setProperty('--app-zoom', '1');
        set({ zoomLevel: 100 });
      },
      addBackgroundTask: (id, label) =>
        set((s) => ({ backgroundTasks: [...s.backgroundTasks, { id, label, progress: 0 }] })),
      updateBackgroundTask: (id, progress) =>
        set((s) => ({
          backgroundTasks: s.backgroundTasks.map((t) =>
            t.id === id ? { ...t, progress } : t,
          ),
        })),
      removeBackgroundTask: (id) =>
        set((s) => ({ backgroundTasks: s.backgroundTasks.filter((t) => t.id !== id) })),
    }),
    {
      name: 'novem-app',
      partialize: (state) => ({
        themeMode: state.themeMode,
        zoomLevel: state.zoomLevel,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          document.documentElement.setAttribute('data-theme', state.themeMode);
          if (state.zoomLevel !== 100) {
            document.documentElement.style.setProperty('--app-zoom', String(state.zoomLevel / 100));
          }
        }
      },
    },
  ),
);
