import { useMemo, useState } from 'react';
import { Typography, Tag, Tooltip, Button, Input } from 'antd';
import {
  RobotOutlined,
  UserOutlined,
  DatabaseOutlined,
  ApiOutlined,
  InfoCircleOutlined,
  LikeOutlined,
  LikeFilled,
  DislikeOutlined,
  DislikeFilled,
  EditOutlined,
  CheckOutlined,
  CloseOutlined,
} from '@ant-design/icons';

import type { CopilotMessage, FeedbackRating } from '@/types/copilot';

import styles from './ChatMessage.module.css';

const { Text } = Typography;
const { TextArea } = Input;

interface ChatMessageProps {
  message: CopilotMessage;
  onFeedback?: (messageId: string, rating: FeedbackRating, correction?: string) => void;
}

const SOURCE_CONFIG: Record<string, { label: string; color: string }> = {
  analytics: { label: 'Analytics Engine', color: 'green' },
  ollama: { label: 'AI Model', color: 'blue' },
  system: { label: 'System', color: 'default' },
  fallback: { label: 'Fallback', color: 'orange' },
  error: { label: 'Error', color: 'red' },
};

export function ChatMessage({ message, onFeedback }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const sourceInfo = message.source ? SOURCE_CONFIG[message.source] : null;
  const [showCorrection, setShowCorrection] = useState(false);
  const [correctionText, setCorrectionText] = useState('');

  const canRate = !isUser && message.messageId && message.source !== 'error';

  const formattedTime = useMemo(() => {
    const d = new Date(message.timestamp);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }, [message.timestamp]);

  const renderedContent = useMemo(() => {
    if (isUser) return message.content;
    return formatMarkdown(message.content);
  }, [message.content, isUser]);

  const handleRate = (rating: FeedbackRating) => {
    if (!message.messageId || !onFeedback) return;

    if (rating === message.feedback) {
      onFeedback(message.messageId, 0);
      return;
    }

    if (rating === -1) {
      setShowCorrection(true);
    } else {
      setShowCorrection(false);
      setCorrectionText('');
      onFeedback(message.messageId, rating);
    }
  };

  const handleSubmitCorrection = () => {
    if (!message.messageId || !onFeedback) return;
    onFeedback(message.messageId, -1, correctionText || undefined);
    setShowCorrection(false);
    setCorrectionText('');
  };

  const handleCancelCorrection = () => {
    setShowCorrection(false);
    setCorrectionText('');
  };

  return (
    <div className={`${styles.message} ${isUser ? styles.user : styles.assistant}`}>
      <div className={styles.avatar}>
        {isUser ? <UserOutlined /> : <RobotOutlined />}
      </div>
      <div className={styles.bubble}>
        {isUser ? (
          <div className={styles.content}>{renderedContent}</div>
        ) : (
          <div
            className={styles.content}
            dangerouslySetInnerHTML={{ __html: renderedContent as string }}
          />
        )}

        {!isUser && message.correctedQuestion && (
          <div className={styles.correctionHint}>
            <InfoCircleOutlined /> Interpreted as: &ldquo;{message.correctedQuestion}&rdquo;
          </div>
        )}

        <div className={styles.meta}>
          <Text className={styles.time}>{formattedTime}</Text>
          {sourceInfo && (
            <Tooltip title={message.model ? `Model: ${message.model}` : sourceInfo.label}>
              <Tag
                className={styles.sourceTag}
                color={sourceInfo.color}
                icon={message.source === 'analytics' ? <DatabaseOutlined /> : message.source === 'ollama' ? <ApiOutlined /> : <InfoCircleOutlined />}
              >
                {sourceInfo.label}
              </Tag>
            </Tooltip>
          )}

          {canRate && (
            <div className={styles.feedbackActions}>
              <Tooltip title="Good answer">
                <Button
                  type="text"
                  size="small"
                  className={`${styles.feedbackBtn} ${message.feedback === 1 ? styles.feedbackActive : ''}`}
                  icon={message.feedback === 1 ? <LikeFilled /> : <LikeOutlined />}
                  onClick={() => handleRate(1)}
                />
              </Tooltip>
              <Tooltip title="Bad answer">
                <Button
                  type="text"
                  size="small"
                  className={`${styles.feedbackBtn} ${message.feedback === -1 ? styles.feedbackActive : ''}`}
                  icon={message.feedback === -1 ? <DislikeFilled /> : <DislikeOutlined />}
                  onClick={() => handleRate(-1)}
                />
              </Tooltip>
            </div>
          )}
        </div>

        {showCorrection && (
          <div className={styles.correctionArea}>
            <div className={styles.correctionHeader}>
              <EditOutlined />
              <Text className={styles.correctionLabel}>What should the answer be?</Text>
            </div>
            <TextArea
              className={styles.correctionInput}
              value={correctionText}
              onChange={(e) => setCorrectionText(e.target.value)}
              placeholder="Optional: provide the correct answer so I can learn from it..."
              autoSize={{ minRows: 2, maxRows: 4 }}
            />
            <div className={styles.correctionActions}>
              <Button
                size="small"
                type="primary"
                icon={<CheckOutlined />}
                onClick={handleSubmitCorrection}
              >
                Submit
              </Button>
              <Button
                size="small"
                icon={<CloseOutlined />}
                onClick={handleCancelCorrection}
              >
                Skip
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function formatMarkdown(text: string): string {
  let html = escapeHtml(text);
  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Line breaks
  html = html.replace(/\n/g, '<br/>');
  // Lists (- item)
  html = html.replace(/(?:^|<br\/>)\s*- (.+?)(?=<br\/>|$)/g, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
  // Numbered lists
  html = html.replace(/(?:^|<br\/>)\s*\d+\.\s+(.+?)(?=<br\/>|$)/g, '<li>$1</li>');
  return html;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
