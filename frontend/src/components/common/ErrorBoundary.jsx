import { Component } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

/**
 * ErrorBoundary
 *
 * Catches JavaScript errors anywhere in their child component tree,
 * logs those errors, and displays a graceful fallback UI instead of crashing the tree.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      const label = this.props.fallbackLabel || 'this view';
      return (
        <div className="error-boundary-card">
          <div className="error-boundary-icon-wrap">
            <AlertTriangle size={28} />
          </div>

          <div>
            <h3 className="error-boundary-title">
              Unable to load {label}
            </h3>
            <p className="error-boundary-message">
              An unexpected runtime error occurred while rendering this screen. You can try reloading the view or returning to the generator.
            </p>
          </div>

          {this.state.error?.message && (
            <div className="error-boundary-details">
              {this.state.error.message}
            </div>
          )}

          <div className="error-boundary-actions">
            <button
              type="button"
              onClick={this.handleReset}
              className="btn-primary"
            >
              <RefreshCw size={14} />
              <span>Retry View</span>
            </button>

            <button
              type="button"
              onClick={() => {
                window.location.href = '/';
              }}
              className="btn-secondary"
            >
              <Home size={14} />
              <span>Back to Home</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
