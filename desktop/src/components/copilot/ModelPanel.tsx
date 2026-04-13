import { useState } from 'react';
import { Button, Tag, Tooltip, Popconfirm, Spin, Typography, Badge } from 'antd';
import {
  ArrowUpOutlined,
  CloseCircleOutlined,
  CloudDownloadOutlined,
  DeleteOutlined,
  ReloadOutlined,
  SwapOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';

import type { ModelRecommendations, OllamaModel, OllamaStatus } from '@/types/copilot';

import styles from './ModelPanel.module.css';

const { Text } = Typography;

interface ModelPanelProps {
  status: OllamaStatus | null;
  models: OllamaModel[];
  activeModel: string;
  installingModel: string | null;
  recommendations: ModelRecommendations | null;
  onSetActive: (modelId: string) => void;
  onInstall: (modelId: string) => void;
  onDelete: (modelId: string) => void;
  onRefresh: () => void;
}

const TIER_COLORS: Record<string, string> = {
  starter: 'green',
  mid: 'blue',
  advanced: 'purple',
};

const TIER_LABELS: Record<string, string> = {
  starter: 'Starter',
  mid: 'Balanced',
  advanced: 'Advanced',
};

export function ModelPanel({
  status,
  models,
  activeModel,
  installingModel,
  recommendations,
  onSetActive,
  onInstall,
  onDelete,
  onRefresh,
}: ModelPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const isAvailable = status?.available ?? false;

  const activeModelObj = models.find((m) => m.id === activeModel);
  const activeModelName = activeModelObj?.name || activeModel;
  const highPrioCount = recommendations?.recommendations.filter(
    (r) => r.priority === 'high'
  ).length ?? 0;

  return (
    <div className={styles.panel}>
      <button className={styles.toggle} onClick={() => setExpanded(!expanded)}>
        <div className={styles.toggleLeft}>
          <span className={`${styles.dot} ${isAvailable ? styles.dotOnline : styles.dotOffline}`} />
          <Text className={styles.toggleLabel}>
            {isAvailable ? activeModelName : 'Ollama Offline'}
          </Text>
          {isAvailable && activeModelObj && (
            <Tag color={TIER_COLORS[activeModelObj.tier]} className={styles.tierTag}>
              {TIER_LABELS[activeModelObj.tier]}
            </Tag>
          )}
        </div>
        <div className={styles.toggleRight}>
          {highPrioCount > 0 && (
            <Badge count={highPrioCount} size="small" />
          )}
          <SwapOutlined className={styles.toggleIcon} />
        </div>
      </button>

      {expanded && (
        <div className={styles.dropdown}>
          <div className={styles.dropdownHeader}>
            <Text className={styles.dropdownTitle}>AI Models</Text>
            <div className={styles.headerActions}>
              {isAvailable && status?.url && (
                <Text className={styles.urlLabel}>{status.url}</Text>
              )}
              <Tooltip title="Refresh status">
                <Button
                  type="text"
                  size="small"
                  icon={<ReloadOutlined />}
                  onClick={onRefresh}
                />
              </Tooltip>
            </div>
          </div>

          {!isAvailable && (
            <div className={styles.offlineMsg}>
              <CloseCircleOutlined />
              <Text className={styles.offlineText}>
                {status?.reason || 'Ollama is not running. Start it to use AI models.'}
              </Text>
            </div>
          )}

          {/* Recommendations banner */}
          {recommendations && recommendations.recommendations.length > 0 && (
            <div className={styles.recsSection}>
              <div className={styles.recsBanner}>
                <ThunderboltOutlined className={styles.recsIcon} />
                <Text className={styles.recsMessage}>{recommendations.message}</Text>
              </div>
              {recommendations.recommendations
                .filter((r) => r.priority === 'high')
                .map((rec) => (
                  <div key={rec.model_id} className={styles.recItem}>
                    <div className={styles.recInfo}>
                      <Text className={styles.recTitle}>
                        {rec.type === 'switch' ? <SwapOutlined /> : <ArrowUpOutlined />}
                        {' '}{rec.title}
                      </Text>
                      <Text className={styles.recDesc}>{rec.description}</Text>
                    </div>
                    <Button
                      size="small"
                      type="primary"
                      ghost
                      onClick={() => {
                        if (rec.type === 'switch') onSetActive(rec.model_id);
                        else onInstall(rec.model_id);
                      }}
                    >
                      {rec.type === 'switch' ? 'Switch' : 'Install'}
                    </Button>
                  </div>
                ))}
            </div>
          )}

          {/* Status summary */}
          {isAvailable && recommendations && (
            <div className={styles.statusBar}>
              <Text className={styles.statusText}>
                {recommendations.installed_count}/{recommendations.total_count} models installed
              </Text>
              {recommendations.status === 'complete' && (
                <Tag color="green" className={styles.completeTag}>All set</Tag>
              )}
            </div>
          )}

          <div className={styles.modelList}>
            {/* Installed models — selectable */}
            {models.filter((m) => m.installed).map((model) => {
              const isActive = model.id === activeModel;

              return (
                <div
                  key={model.id}
                  className={`${styles.modelItem} ${isActive ? styles.modelActive : ''}`}
                >
                  <div className={styles.modelInfo}>
                    <div className={styles.modelName}>
                      {model.name}
                      <Tag color={TIER_COLORS[model.tier]} className={styles.tierTagSmall}>
                        {model.params}
                      </Tag>
                      {isActive && <Tag color="green" className={styles.activeTag}>Active</Tag>}
                    </div>
                    <div className={styles.modelDesc}>
                      {model.description} · {model.size_gb} GB
                    </div>
                  </div>
                  <div className={styles.modelActions}>
                    {!isActive && (
                      <Button
                        size="small"
                        type="primary"
                        ghost
                        onClick={() => onSetActive(model.id)}
                        disabled={!isAvailable}
                      >
                        Use
                      </Button>
                    )}
                    {!isActive && (
                      <Popconfirm
                        title="Delete this model?"
                        description={`This will free ~${model.size_gb} GB of disk space.`}
                        onConfirm={() => onDelete(model.id)}
                      >
                        <Button
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                        />
                      </Popconfirm>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Not installed — available to download */}
            {models.some((m) => !m.installed) && (
              <>
                <div className={styles.sectionDivider}>
                  <Text className={styles.sectionLabel}>Available to install</Text>
                </div>
                {models.filter((m) => !m.installed).map((model) => {
                  const isInstalling = model.id === installingModel;
                  return (
                    <div key={model.id} className={styles.modelItem}>
                      <div className={styles.modelInfo}>
                        <div className={styles.modelName}>
                          {model.name}
                          <Tag color={TIER_COLORS[model.tier]} className={styles.tierTagSmall}>
                            {model.params}
                          </Tag>
                        </div>
                        <div className={styles.modelDesc}>
                          {model.description} · {model.size_gb} GB
                        </div>
                      </div>
                      <div className={styles.modelActions}>
                        <Button
                          size="small"
                          icon={isInstalling ? <Spin size="small" /> : <CloudDownloadOutlined />}
                          onClick={() => onInstall(model.id)}
                          disabled={!isAvailable || !!installingModel}
                          loading={isInstalling}
                        >
                          {isInstalling ? 'Installing…' : `Install (${model.size_gb} GB)`}
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
