import React, { lazy, Suspense } from "react";
import { BrowserRouter, Switch, Route } from "react-router-dom";

import "./App.css";
import "./colors.css";

function lazyLoadRetry(fn, retriesLeft = 5, interval = 1000) {
  return new Promise((resolve, reject) => {
    fn()
      .then(resolve)
      .catch(() => {
        setTimeout(() => {
          if (retriesLeft === 1) {
            window.location.reload();
          }

          // Passing on "reject" is the important part
          lazyLoadRetry(fn, retriesLeft - 1, interval).then(resolve, reject);
        }, interval);
      });
  });
}

const Archive = lazy(() => lazyLoadRetry(() => import ("./Archive")));

function Loading() {
  return <div className="status">Loading website ...</div>;
}

function NotFound() {
  return <div className="status error">There's nothing to be found here! :(</div>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<Loading />}>
        <Switch>
          <Route path="/archives/:id">
            <Archive />
          </Route>
          <Route path="*">
            <NotFound />
          </Route>
        </Switch>
      </Suspense>
    </BrowserRouter>
  );
}
