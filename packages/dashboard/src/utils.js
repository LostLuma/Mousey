import {lazy} from "react";

/**
 * @param {Number} interval
 * @returns {Promise<Null>}
 */
function sleep(interval) {
  return new Promise((resolve) => {
    setTimeout(resolve, interval);
  });
}

/**
 * @param {Function} func
 * @returns {React.LazyExoticComponent<React.ComponentType<any>>}
 */
export function retryingLazy(func) {
  async function importModule(retriesLeft = 5, interval = 500) {
    for (let x = 0; x < retriesLeft; x++) {
      try {
        return await func();
      } catch (e) {
        if (x === 4) {
          throw e;
        }

        await sleep(interval);
      }
    }
  }

  return lazy(importModule);
}
