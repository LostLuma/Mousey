import React, { lazy } from "react";

export function sleep(interval) {
  return new Promise((resolve) => {
    setTimeout(resolve, interval);
  });
}

export function retryingLazy(func) {
  async function importModule() {
    const retries = 5;

    for (let x = 1; x <= retries; x++) {
      try {
        return await func();
      } catch (e) {
        if (x === retries) {
          throw e;
        }

        await sleep(500);
      }
    }
  }

  return lazy(importModule);
}

export class LoadingErrorBoundary extends React.Component {
  constructor(props) {
    super(props);

    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    // Re-throw errors that are
    // Unrelated to loading scripts
    if (error.target.type !== "text/javascript") {
      throw error;
    }

    return { error };
  }

  render() {
    if (!this.state.error) {
      return this.props.children;
    }

    return (
      <div className="status error">
        <p>Unable to load website.</p>
        <p>Refresh the page to retry.</p>
      </div>
    );
  }
}
