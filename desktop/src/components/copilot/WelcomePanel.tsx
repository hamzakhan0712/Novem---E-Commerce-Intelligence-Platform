import { DollarOutlined, TeamOutlined, ShoppingOutlined, HeartOutlined, BulbOutlined } from '@ant-design/icons';

import type { ConversationStarter } from '@/types/copilot';

import styles from './WelcomePanel.module.css';

interface WelcomePanelProps {
  starters: ConversationStarter[];
  suggestions: string[];
  onAsk: (question: string) => void;
}

const ICON_MAP: Record<string, React.ReactNode> = {
  dollar: <DollarOutlined />,
  team: <TeamOutlined />,
  shopping: <ShoppingOutlined />,
  pulse: <HeartOutlined />,
};

export function WelcomePanel({ starters, suggestions, onAsk }: WelcomePanelProps) {
  const hasStarters = starters.length > 0;

  return (
    <div className={styles.welcome}>
      <div className={styles.hero}>
        <BulbOutlined className={styles.heroIcon} />
        <h2 className={styles.heroTitle}>What would you like to know?</h2>
        <p className={styles.heroSub}>
          Ask questions about your store data — revenue, customers, products, and more.
        </p>
      </div>

      {hasStarters ? (
        <div className={styles.starterGrid}>
          {starters.map((group) => (
            <div key={group.category} className={styles.starterCard}>
              <div className={styles.starterHeader}>
                <span className={styles.starterIcon}>
                  {ICON_MAP[group.icon] || <BulbOutlined />}
                </span>
                <span className={styles.starterCategory}>{group.category}</span>
              </div>
              <div className={styles.starterQuestions}>
                {group.questions.map((q) => (
                  <button
                    key={q}
                    className={styles.starterBtn}
                    onClick={() => onAsk(q)}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className={styles.suggestionList}>
          {suggestions.map((q) => (
            <button
              key={q}
              className={styles.suggestionBtn}
              onClick={() => onAsk(q)}
            >
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
