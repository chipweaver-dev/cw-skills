#!/usr/bin/env node
/**
 * Capture stills and measure element boxes from a running review page.
 *
 * The page must support ?t=SEC (freeze at a time) and should support
 * ?record=1 (hide the transport). This script talks to Chrome over CDP:
 *
 *   1. Chrome is already running with --remote-debugging-port=9222.
 *   2. For each time: navigate, wait for fonts/images, measure selectors,
 *      capture a 1080x1920 PNG.
 *
 * Usage:
 *   node cdp_capture.mjs --url http://127.0.0.1:5180/ \
 *     --times 0,25.48,26.3 --out .tmp/shots --selectors ".stage,.sub-band"
 */

import fs from "node:fs";
import path from "node:path";

function usage() {
  console.log(`cdp_capture.mjs

  --url URL             review page (default http://127.0.0.1:5180/)
  --times A,B,C         seconds to freeze (required)
  --out DIR             output directory (default .tmp/shots)
  --prefix NAME         file prefix (default shot)
  --selectors LIST      CSS selectors measured and reported
  --port N              CDP port (default 9222)
  --width N             viewport width (default 1080)
  --height N            viewport height (default 1920)
  --device-scale N      device scale factor (default 1)
  --wait MS             settle time after load (default 700)
  --timeout MS          navigation/load timeout (default 20000)
  --target-url TEXT     pick a CDP page whose URL contains TEXT
  --no-record           do not append record=1
  --help                show this text

Start Chrome separately, for example:
  chrome --remote-debugging-port=9222 --user-data-dir=/tmp/cdp-profile \\
         --window-size=1080,1920 about:blank
`);
}

function parseArgs(argv) {
  const out = {
    url: "http://127.0.0.1:5180/",
    out: ".tmp/shots",
    prefix: "shot",
    selectors: ".stage",
    port: 9222,
    width: 1080,
    height: 1920,
    deviceScale: 1,
    wait: 700,
    timeout: 20000,
    record: true,
    targetUrl: "",
    times: [],
  };
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    const value = argv[i + 1];
    if (key === "--help" || key === "-h") {
      usage();
      process.exit(0);
    } else if (key === "--url") { out.url = value; i += 1; }
    else if (key === "--times") { out.times = String(value).split(",").map(Number).filter(Number.isFinite); i += 1; }
    else if (key === "--out") { out.out = value; i += 1; }
    else if (key === "--prefix") { out.prefix = value; i += 1; }
    else if (key === "--selectors") { out.selectors = value; i += 1; }
    else if (key === "--port") { out.port = Number(value); i += 1; }
    else if (key === "--width") { out.width = Number(value); i += 1; }
    else if (key === "--height") { out.height = Number(value); i += 1; }
    else if (key === "--device-scale") { out.deviceScale = Number(value); i += 1; }
    else if (key === "--wait") { out.wait = Number(value); i += 1; }
    else if (key === "--timeout") { out.timeout = Number(value); i += 1; }
    else if (key === "--target-url") { out.targetUrl = value; i += 1; }
    else if (key === "--no-record") { out.record = false; }
    else { throw new Error("unknown argument: " + key); }
  }
  if (!out.times.length) throw new Error("--times is required, e.g. --times 0,12.5");
  return out;
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

class CDP {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.ws = null;
    this.nextId = 0;
    this.pending = new Map();
  }

  async connect() {
    if (typeof WebSocket === "undefined") {
      throw new Error("global WebSocket is missing; use Node 22+");
    }
    this.ws = new WebSocket(this.wsUrl);
    await new Promise((resolve, reject) => {
      this.ws.addEventListener("open", resolve, { once: true });
      this.ws.addEventListener("error", reject, { once: true });
    });
    this.ws.addEventListener("message", (event) => {
      let message;
      try { message = JSON.parse(event.data); } catch (err) { return; }
      if (!message.id || !this.pending.has(message.id)) return;
      const { resolve, reject } = this.pending.get(message.id);
      this.pending.delete(message.id);
      if (message.error) reject(new Error(JSON.stringify(message.error)));
      else resolve(message.result || {});
    });
  }

  send(method, params = {}) {
    const id = ++this.nextId;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  close() {
    if (this.ws) this.ws.close();
  }
}

async function pickTarget(port, targetUrl) {
  const response = await fetch(`http://127.0.0.1:${port}/json`);
  if (!response.ok) throw new Error(`CDP /json returned ${response.status}`);
  const targets = await response.json();
  const pages = targets.filter((item) => item.type === "page");
  if (!pages.length) {
    throw new Error("no CDP page target; open a tab in the debugging Chrome");
  }
  if (targetUrl) {
    const match = pages.find((item) => (item.url || "").includes(targetUrl));
    if (match) return match;
  }
  return pages[0];
}

function buildUrl(base, time, record) {
  const url = new URL(base);
  url.searchParams.set("t", String(time));
  if (record) url.searchParams.set("record", "1");
  return url.toString();
}

async function waitForReady(cdp, timeout, expectedTime) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    let info = null;
    try {
      const result = await cdp.send("Runtime.evaluate", {
        expression: "JSON.stringify({href: location.href, state: document.readyState})",
        returnByValue: true,
      });
      if (result.result && typeof result.result.value === "string") {
        info = JSON.parse(result.result.value);
      }
    } catch (err) {
      // Navigation can destroy the execution context between polls.
    }
    if (info && info.state === "complete") {
      let sameTime = true;
      if (expectedTime !== undefined) {
        try {
          sameTime = new URL(info.href).searchParams.get("t") === String(expectedTime);
        } catch (err) {
          sameTime = false;
        }
      }
      if (sameTime) return;
    }
    await sleep(100);
  }
  throw new Error("page did not reach readyState=complete for t=" + expectedTime);
}

function measureExpression(selectors) {
  return `(async () => {
    if (document.fonts && document.fonts.ready) {
      try { await document.fonts.ready; } catch (err) {}
    }
    const images = Array.from(document.images || []);
    await Promise.all(images.map((img) => {
      if (img.complete) return Promise.resolve();
      return new Promise((resolve) => {
        img.addEventListener("load", resolve, { once: true });
        img.addEventListener("error", resolve, { once: true });
      });
    }));
    const round = (value) => Math.round(value * 100) / 100;
    const box = (el) => {
      const r = el.getBoundingClientRect();
      return {
        x: round(r.x), y: round(r.y), w: round(r.width), h: round(r.height),
        top: round(r.top), bottom: round(r.bottom),
      };
    };
    const selectors = ${JSON.stringify(selectors)};
    const out = {
      viewport: {
        w: window.innerWidth, h: window.innerHeight,
        dpr: window.devicePixelRatio,
        scrollW: document.documentElement.scrollWidth,
        scrollH: document.documentElement.scrollHeight,
      },
      selectors: {},
      time: typeof window.__filmTime === "number" ? window.__filmTime : null,
    };
    for (const selector of selectors) {
      out.selectors[selector] = Array.from(document.querySelectorAll(selector)).map((el) => ({
        tag: el.tagName,
        text: (el.textContent || "").trim().slice(0, 100),
        ...box(el),
      }));
    }
    return out;
  })()`;
}

async function captureOne(cdp, options, time) {
  const url = buildUrl(options.url, time, options.record);
  await cdp.send("Page.navigate", { url });
  await waitForReady(cdp, options.timeout, time);
  await sleep(options.wait);

  const selectors = options.selectors.split(",").map((item) => item.trim()).filter(Boolean);
  const evaluated = await cdp.send("Runtime.evaluate", {
    expression: measureExpression(selectors),
    awaitPromise: true,
    returnByValue: true,
  });
  if (evaluated.exceptionDetails) {
    throw new Error("measure failed: " + JSON.stringify(evaluated.exceptionDetails));
  }

  const shot = await cdp.send("Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
    captureBeyondViewport: false,
  });
  const stamp = time.toFixed(2).replace(".", "p");
  const file = path.join(options.out, `${options.prefix}_${stamp}.png`);
  fs.writeFileSync(file, Buffer.from(shot.data, "base64"));
  return {
    ...evaluated.result.value,
    time,
    url,
    file,
  };
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  fs.mkdirSync(options.out, { recursive: true });

  const target = await pickTarget(options.port, options.targetUrl);
  console.log(`target: ${target.url}`);
  const cdp = new CDP(target.webSocketDebuggerUrl);
  await cdp.connect();
  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width: options.width,
    height: options.height,
    deviceScaleFactor: options.deviceScale,
    mobile: false,
  });

  const captures = [];
  try {
    for (const time of options.times) {
      process.stdout.write(`capture t=${time} ... `);
      const item = await captureOne(cdp, options, time);
      captures.push(item);
      const stage = item.selectors[".stage"] && item.selectors[".stage"][0];
      console.log(stage ? `stage ${stage.w}x${stage.h}` : "ok");
    }
  } finally {
    cdp.close();
  }

  const report = {
    url: options.url,
    width: options.width,
    height: options.height,
    deviceScale: options.deviceScale,
    capturedAt: new Date().toISOString(),
    captures,
  };
  const reportPath = path.join(options.out, "captures.json");
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + "\n");
  console.log(`wrote ${captures.length} still(s) and ${reportPath}`);
}

main().catch((err) => {
  console.error("ERROR: " + (err && err.message ? err.message : String(err)));
  process.exit(1);
});
