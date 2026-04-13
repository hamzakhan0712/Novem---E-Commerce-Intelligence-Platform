import { useState } from 'react';

import { Button, Input, Modal, message } from 'antd';
import {
  LockOutlined,
  QuestionCircleOutlined,
  DashboardOutlined,
  LineChartOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';

import { useAuthStore } from '@/stores/authStore';
import { useAppStore } from '@/stores/appStore';
import TitleBar from '@/components/shell/TitleBar';
import novemLogo from '@/assets/images/novem_logo.png';

import welcomeDark from '@/assets/images/welcome_dark.png';
import welcomeLight from '@/assets/images/welcome_light.png';

import styles from './Login.module.css';

export default function Login() {
  const { user, loading, error, login, clearError, getSecurityQuestion, forgotPassword, resetPassword } = useAuthStore();
  const themeMode = useAppStore((s) => s.themeMode);
  const [password, setPassword] = useState('');

  // Forgot password state
  const [forgotOpen, setForgotOpen] = useState(false);
  const [forgotStep, setForgotStep] = useState<'answer' | 'reset'>('answer');
  const [securityQuestion, setSecurityQuestion] = useState('');
  const [securityAnswerInput, setSecurityAnswerInput] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotError, setForgotError] = useState('');

  const heroBg = themeMode === 'dark' ? welcomeDark : welcomeLight;

  const displayName = user?.name ?? 'there';
  const initials = displayName
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  const handleSubmit = () => {
    if (!password.trim()) return;
    login(password);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSubmit();
  };

  const handleOpenForgot = async () => {
    setForgotError('');
    setSecurityAnswerInput('');
    setNewPassword('');
    setConfirmNewPassword('');
    setForgotStep('answer');
    setForgotLoading(true);
    setForgotOpen(true);

    const question = await getSecurityQuestion();
    if (question) {
      setSecurityQuestion(question);
    } else {
      setForgotError('No security question was configured during setup.');
    }
    setForgotLoading(false);
  };

  const handleVerifyAnswer = async () => {
    if (!securityAnswerInput.trim()) return;
    setForgotLoading(true);
    setForgotError('');
    try {
      const token = await forgotPassword(securityAnswerInput.trim());
      setResetToken(token);
      setForgotStep('reset');
    } catch {
      setForgotError('Incorrect answer. Please try again.');
    }
    setForgotLoading(false);
  };

  const handleResetPassword = async () => {
    if (newPassword.length < 4 || newPassword !== confirmNewPassword) return;
    setForgotLoading(true);
    setForgotError('');
    try {
      await resetPassword(resetToken, newPassword);
      message.success('Password reset successfully');
      setForgotOpen(false);
    } catch {
      setForgotError('Failed to reset password. Please try again.');
    }
    setForgotLoading(false);
  };

  return (
    <div className={styles.login}>
      <TitleBar minimal />
      <div className={styles.body}>
        <div
          className={styles.heroSide}
          style={{ backgroundImage: `url(${heroBg})` }}
        >
          <div className={styles.heroBrand}>
            <img src={novemLogo} alt="NOVEM" className={styles.heroLogo} />
            <div className={styles.heroBrandText}>
              <h1 className={styles.heroTitle}>NOVEM</h1>
              <p className={styles.heroTagline}>E-Commerce Intelligence Platform</p>
            </div>
          </div>

          <div className={styles.heroFeaturesLarge}>
            <div className={styles.heroFeatureLarge}>
              <DashboardOutlined className={styles.heroFeatureLargeIcon} />
              <div>
                <h3 className={styles.heroFeatureLargeTitle}>Auto-Analysis &amp; KPI Dashboards</h3>
                <p className={styles.heroFeatureLargeDesc}>Revenue, customer value, order trends, and at-risk alerts — automatically generated the moment you import data.</p>
              </div>
            </div>
            <div className={styles.heroFeatureLarge}>
              <LineChartOutlined className={styles.heroFeatureLargeIcon} />
              <div>
                <h3 className={styles.heroFeatureLargeTitle}>Smart Forecasting</h3>
                <p className={styles.heroFeatureLargeDesc}>AI-powered predictions for sales, demand, and seasonal patterns with unusual activity detection built in.</p>
              </div>
            </div>
            <div className={styles.heroFeatureLarge}>
              <RobotOutlined className={styles.heroFeatureLargeIcon} />
              <div>
                <h3 className={styles.heroFeatureLargeTitle}>AI Copilot</h3>
                <p className={styles.heroFeatureLargeDesc}>Ask questions in plain English and get instant root-cause analysis powered by a local LLM — no cloud required.</p>
              </div>
            </div>
            <div className={styles.heroFeatureLarge}>
              <SafetyCertificateOutlined className={styles.heroFeatureLargeIcon} />
              <div>
                <h3 className={styles.heroFeatureLargeTitle}>100% Local &amp; Private</h3>
                <p className={styles.heroFeatureLargeDesc}>DuckDB analytics, SQLite storage, zero telemetry. Your data never leaves your machine — ever.</p>
              </div>
            </div>
          </div>
        </div>

        <div className={styles.formSide}>
          <div className={styles.card}>
            <div className={styles.header}>
              {user?.avatar_photo ? (
                <img src={user.avatar_photo} alt="" className={styles.avatarPhoto} />
              ) : (
                <div className={styles.avatarFallback}>{initials}</div>
              )}
              <h2 className={styles.greeting}>Welcome back, {displayName}</h2>
              <p className={styles.subtitle}>Enter your password to continue</p>
            </div>

            <div className={styles.form}>
              <Input.Password
                size="large"
                prefix={<LockOutlined />}
                placeholder="Password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (error) clearError();
                }}
                onKeyDown={handleKeyDown}
                status={error ? 'error' : undefined}
                autoFocus
              />

              {error && <p className={styles.error}>{error}</p>}

              <div className={styles.actions}>
                <Button
                  type="primary"
                  size="large"
                  block
                  loading={loading}
                  onClick={handleSubmit}
                  disabled={!password.trim()}
                >
                  Unlock
                </Button>
                <Button type="link" size="small" onClick={handleOpenForgot} className={styles.forgotLink}>
                  Forgot Password?
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <Modal
        title="Reset Password"
        open={forgotOpen}
        onCancel={() => setForgotOpen(false)}
        footer={null}
        width={420}
        centered
        destroyOnClose
      >
        {forgotStep === 'answer' && (
          <div className={styles.forgotForm}>
            {securityQuestion ? (
              <>
                <p className={styles.forgotDesc}>Answer your security question to reset your password.</p>
                <div className={styles.forgotQuestion}>
                  <QuestionCircleOutlined style={{ color: 'var(--novem-accent)', marginRight: 8 }} />
                  {securityQuestion}
                </div>
                <Input
                  size="large"
                  placeholder="Your answer"
                  value={securityAnswerInput}
                  onChange={(e) => setSecurityAnswerInput(e.target.value)}
                  onPressEnter={handleVerifyAnswer}
                  autoFocus
                />
                {forgotError && <p className={styles.error}>{forgotError}</p>}
                <Button
                  type="primary"
                  block
                  size="large"
                  loading={forgotLoading}
                  disabled={!securityAnswerInput.trim()}
                  onClick={handleVerifyAnswer}
                  style={{ marginTop: 8 }}
                >
                  Verify Answer
                </Button>
              </>
            ) : (
              <>
                <p className={styles.error}>{forgotError || 'Loading...'}</p>
              </>
            )}
          </div>
        )}

        {forgotStep === 'reset' && (
          <div className={styles.forgotForm}>
            <p className={styles.forgotDesc}>Set your new password.</p>
            <Input.Password
              size="large"
              prefix={<LockOutlined />}
              placeholder="New password (min 4 characters)"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoFocus
            />
            <Input.Password
              size="large"
              prefix={<LockOutlined />}
              placeholder="Confirm new password"
              value={confirmNewPassword}
              onChange={(e) => setConfirmNewPassword(e.target.value)}
              status={confirmNewPassword && newPassword !== confirmNewPassword ? 'error' : undefined}
              style={{ marginTop: 12 }}
            />
            {forgotError && <p className={styles.error}>{forgotError}</p>}
            <Button
              type="primary"
              block
              size="large"
              loading={forgotLoading}
              disabled={newPassword.length < 4 || newPassword !== confirmNewPassword}
              onClick={handleResetPassword}
              style={{ marginTop: 12 }}
            >
              Reset Password
            </Button>
          </div>
        )}
      </Modal>
    </div>
  );
}
