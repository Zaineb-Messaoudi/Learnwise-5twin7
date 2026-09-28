import React from 'react';
import { Link } from 'react-router-dom';

export class AppErrorBoundary extends React.Component {
  state = { hasError: false };
  static getDerivedStateFromError() { return { hasError: true }; }
  render() { if (!this.state.hasError) return this.props.children; return <main className="error-boundary"><span className="eyebrow">TEMPORARY INTERRUPTION</span><h1>Learnwise needs a reset.</h1><p>Something went wrong while rendering this view.</p><div><button type="button" className="button" onClick={() => window.location.reload()}>Reload view</button><Link className="button button-secondary" to="/student/dashboard">Back to dashboard</Link></div></main>; }
}
