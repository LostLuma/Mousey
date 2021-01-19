import {
  getAssetFromKV,
  MethodNotAllowedError,
  NotFoundError,
  serveSinglePageApp,
} from "@cloudflare/kv-asset-handler";

const DAY = 86400;
const YEAR = DAY * 365;

class HTTPError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function getCacheTTL(path) {
  // Match all paths with hashes in the filename
  // Eg. /blobluma.17155d19.png, but not /blobluma.png
  const isVersioned = /\/(?:[^/]+\.){2}[^/]+$/.test(path);

  // As versioned assets will update their URLs when changed
  // We can return a very long (1 year) cache lifetime for these
  return isVersioned ? YEAR : DAY;
}

export default async function getStaticAsset(event) {
  const path = new URL(event.request.url).pathname;

  const cacheControl = {
    edgeTTL: DAY,
    browserTTL: getCacheTTL(path),
  };

  try {
    return await getAssetFromKV(event, {
      cacheControl,
      mapRequestToAsset: serveSinglePageApp,
    });
  } catch (e) {
    if (e instanceof NotFoundError) {
      throw new HTTPError(404, "File not found.");
    } else if (e instanceof MethodNotAllowedError) {
      throw new HTTPError(405, "Method now allowed.");
    }

    throw e; // Re-throw InternalError for debugging
  }
}

async function handleEvent(event) {
  try {
    return await getStaticAsset(event);
  } catch (e) {
    if (!(e instanceof HTTPError)) {
      throw e;
    }

    const headers = {
      "Cache-Control": "no-cache",
      "Content-Type": "text/plain; charset=UTF-8",
    };
    return new Response(e.message, { headers, status: e.status });
  }
}

addEventListener("fetch", (event) => {
  event.respondWith(handleEvent(event));
});
