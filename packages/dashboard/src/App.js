import React, { Suspense } from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";

import { LoadingErrorBoundary, retryingLazy } from "./utils";

import "./App.css";
import "./colors.css";

const Archive = retryingLazy(() => import("./Archive"));

function Loading() {
  return <div className="status">Loading website ...</div>;
}

function NotFound() {
  return <div className="status error">There's nothing to be found here! :(</div>;
}

export default function App() {
  return (
    <BrowserRouter>
      <LoadingErrorBoundary>
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
      </LoadingErrorBoundary>
    </BrowserRouter>
  );
}
