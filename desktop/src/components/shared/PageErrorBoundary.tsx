import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

import { Button, Result } from 'antd';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export class PageErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Page error boundary caught:', error, info.componentStack);
  }

  private handleGoHome = () => {
    this.setState({ hasError: false });
    window.location.hash = '#/dashboard';
  };

  private handleReload = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="Something went wrong on this page"
          extra={[
            <Button key="home" type="primary" onClick={this.handleGoHome}>
              Go to Dashboard
            </Button>,
            <Button key="reload" onClick={this.handleReload}>
              Reload Page
            </Button>,
          ]}
        />
      );
    }

    return this.props.children;
  }
}
