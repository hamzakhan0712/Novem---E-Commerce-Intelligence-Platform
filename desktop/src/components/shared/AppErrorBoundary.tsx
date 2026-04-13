import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

import { Button, Result, Typography } from 'antd';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  errorMessage: string;
}

export class AppErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error.message || 'Unknown error' };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('App error boundary caught:', error, info.componentStack);
  }

  private handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', padding: 24 }}>
          <Result
            status="500"
            title="Something went wrong"
            subTitle="The application encountered an unexpected error. This may happen if the analytics engine is not running."
            extra={[
              <Button key="reload" type="primary" onClick={this.handleReload}>
                Reload Application
              </Button>,
            ]}
          >
            <Typography.Paragraph type="secondary" style={{ textAlign: 'center' }}>
              If this keeps happening, try restarting Novem from the system tray.
            </Typography.Paragraph>
          </Result>
        </div>
      );
    }

    return this.props.children;
  }
}
