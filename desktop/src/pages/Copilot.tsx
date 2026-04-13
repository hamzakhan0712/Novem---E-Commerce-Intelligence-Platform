import { useState, useEffect, useRef } from 'react';
import { Button, Tooltip } from 'antd';
import { SendOutlined, ClearOutlined } from '@ant-design/icons';

import { useCopilotData } from '@/hooks/useCopilotData';
import { markPageVisited } from '@/components/dashboard/GettingStartedChecklist';
import { useStoreStore } from '@/stores/storeStore';
import { DataGate } from '@/components/shared';
import { ChatMessage, ModelPanel, TypingIndicator, WelcomePanel } from '@/components/copilot';

import type { FeedbackRating } from '@/types/copilot';

import styles from './Copilot.module.css';

export default function Copilot() {
  const activeStoreId = useStoreStore((s) => s.activeStoreId);
  const {
    messages,
    suggestions,
    starters,
    loading,
    ollamaStatus,
    models,
    activeModel,
    installingModel,
    recommendations,
    askQuestion,
    submitFeedback,
    clearMessages,
    setActiveModel,
    installModel,
    deleteModel,
    refreshStatus,
    refreshModels,
    refreshRecommendations,
  } = useCopilotData();

  const [input, setInput] = useState('');
  const messageEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { markPageVisited('copilot'); }, []);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    const question = input.trim();
    if (!question || !activeStoreId || loading) return;
    setInput('');
    askQuestion(activeStoreId, question);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleAsk = (question: string) => {
    if (!activeStoreId || loading) return;
    askQuestion(activeStoreId, question);
  };

  const handleFeedback = (messageId: string, rating: FeedbackRating, correction?: string) => {
    if (!activeStoreId) return;
    submitFeedback(activeStoreId, messageId, rating, correction);
  };

  const handleRefresh = () => {
    refreshStatus();
    refreshModels();
    refreshRecommendations();
  };

  if (!activeStoreId) {
    return (
      <DataGate pageKey="copilot" className={styles.page}>
        <div />
      </DataGate>
    );
  }

  return (
    <DataGate pageKey="copilot" className={styles.page}>
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>AI Copilot</h1>
          <span className={styles.subtitle}>Ask questions about your business data</span>
        </div>
        <div className={styles.headerRight}>
          <ModelPanel
            status={ollamaStatus}
            models={models}
            activeModel={activeModel}
            installingModel={installingModel}
            recommendations={recommendations}
            onSetActive={setActiveModel}
            onInstall={installModel}
            onDelete={deleteModel}
            onRefresh={handleRefresh}
          />
          {messages.length > 0 && (
            <Tooltip title="Clear conversation">
              <Button icon={<ClearOutlined />} size="small" onClick={clearMessages} />
            </Tooltip>
          )}
        </div>
      </div>

      <div className={styles.messageArea}>
        {messages.length === 0 ? (
          <WelcomePanel
            starters={starters}
            suggestions={suggestions}
            onAsk={handleAsk}
          />
        ) : (
          <div className={styles.messageList}>
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} onFeedback={handleFeedback} />
            ))}
            {loading && <TypingIndicator />}
            <div ref={messageEndRef} />
          </div>
        )}
      </div>

      <div className={styles.inputArea}>
        <div className={styles.inputWrapper}>
          <input
            className={styles.chatInput}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your data..."
            disabled={loading}
          />
          <Button
            className={styles.sendBtn}
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={loading}
            disabled={!input.trim()}
          />
        </div>
        <p className={styles.inputHint}>
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
    </DataGate>
  );
}
