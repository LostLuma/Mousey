import { lazy } from "react";

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
