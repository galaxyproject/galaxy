import { gunzipSync } from "node:zlib";

/**
 * Vite plugin to enable HMR when developing against a Galaxy server.
 *
 * The problem: Galaxy serves HTML from Mako templates that reference production
 * bundles at /static/dist/*.bundled.js. When using Vite's dev server as a proxy,
 * the browser loads these production bundles instead of Vite's dev entry points,
 * so HMR doesn't work.
 *
 * The solution: Intercept HTML responses from Galaxy and rewrite them to:
 * 1. Inject Vite's HMR client script
 * 2. Replace production bundle URLs with Vite dev server entry points
 * 3. Remove production CSS (Vite injects CSS via JS in dev mode)
 *
 * This allows `GALAXY_URL=https://usegalaxy.org yarn develop` to work with
 * full HMR support without any server-side changes.
 */

/**
 * Stub script to inject before any modules load.
 * This creates window.config and window.bundleEntries stubs that queue
 * calls until the real modules load and process them.
 */
const CONFIG_STUB_SCRIPT = `
<script>
// Stub config object - queues set() calls until the real module loads
(function() {
    var configQueue = [];
    window.config = {
        set: function() {
            // Queue the arguments for later processing
            configQueue.push(Array.prototype.slice.call(arguments));
        },
        _queue: configQueue,
        _processQueue: function(realSet) {
            configQueue.forEach(function(args) {
                realSet.apply(null, args);
            });
            configQueue.length = 0;
        }
    };
    // Stub bundleEntries - will be replaced by real module
    window.bundleEntries = {};
})();
</script>`;

/**
 * Transform Galaxy HTML to use Vite dev server entry points
 * @param {string} html - The HTML content from Galaxy
 * @returns {string} - Transformed HTML with Vite dev URLs
 */
function transformGalaxyHtml(html) {
    // Inject stub config FIRST (synchronous, non-module) so it's available immediately
    // Then inject Vite client for HMR
    html = html.replace(
        /<head([^>]*)>/i,
        "<head$1>" + CONFIG_STUB_SCRIPT + '\n    <script type="module" src="/@vite/client"></script>',
    );

    // Rewrite libs.bundled.js to dev entry point
    // Match script tags with or without type="module"
    html = html.replace(
        /<script[^>]*src="[^"]*\/static\/dist\/libs\.bundled\.js[^"]*"[^>]*><\/script>/gi,
        '<script type="module" src="/src/entry/libs.js"></script>',
    );

    // Rewrite analysis.bundled.js to dev entry point
    html = html.replace(
        /<script[^>]*src="[^"]*\/static\/dist\/analysis\.bundled\.js[^"]*"[^>]*><\/script>/gi,
        '<script type="module" src="/src/entry/analysis/index.ts"></script>',
    );

    // Rewrite generic.bundled.js to dev entry point
    html = html.replace(
        /<script[^>]*src="[^"]*\/static\/dist\/generic\.bundled\.js[^"]*"[^>]*><\/script>/gi,
        '<script type="module" src="/src/entry/generic.js"></script>',
    );

    // Remove production CSS link - Vite injects CSS via JS modules in dev mode
    html = html.replace(
        /<link[^>]*href="[^"]*\/static\/dist\/base\.css[^"]*"[^>]*>/gi,
        "<!-- base.css removed - Vite injects CSS via JS in dev mode -->",
    );

    return html;
}

/**
 * Vite plugin that transforms proxied Galaxy HTML responses for HMR support
 */
export function galaxyDevServerPlugin() {
    return {
        name: "galaxy-dev-server",
        configureServer(server) {
            // Add middleware to intercept and transform HTML responses
            server.middlewares.use((req, res, next) => {
                // Store original methods
                const originalWrite = res.write.bind(res);
                const originalEnd = res.end.bind(res);

                // Buffer to collect response body
                const chunks = [];
                let isHtml = false;

                // Override write to collect chunks
                res.write = function (chunk, encoding, callback) {
                    if (chunk) {
                        chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk, encoding));
                    }
                    // Don't write yet - we'll write in end()
                    if (typeof encoding === "function") {
                        encoding(); // encoding is actually the callback
                    } else if (typeof callback === "function") {
                        callback();
                    }
                    return true;
                };

                // Override end to transform and send response
                res.end = function (chunk, encoding, callback) {
                    if (chunk) {
                        chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk, encoding));
                    }

                    // Check content type
                    const contentType = res.getHeader("content-type");
                    isHtml = contentType && contentType.toString().includes("text/html");

                    // Combine all chunks
                    let body = Buffer.concat(chunks);

                    // Transform HTML responses that contain Galaxy bundles
                    if (isHtml) {
                        // Decompress gzip responses (common from remote Galaxy servers)
                        const contentEncoding = res.getHeader("content-encoding");
                        if (contentEncoding === "gzip") {
                            try {
                                body = gunzipSync(body);
                            } catch (e) {
                                // If decompression fails, continue with original body
                                console.warn("[galaxy-dev-server] Failed to decompress gzip response:", e.message);
                            }
                        }

                        let htmlString = body.toString("utf-8");
                        if (htmlString.includes("bundled.js") || htmlString.includes("/static/dist/")) {
                            htmlString = transformGalaxyHtml(htmlString);
                            body = Buffer.from(htmlString, "utf-8");

                            // Update content-length header
                            res.setHeader("content-length", body.length);

                            // Remove content-encoding since we've decompressed it
                            res.removeHeader("content-encoding");
                        }
                    }

                    // Send the response
                    originalWrite(body);

                    if (typeof encoding === "function") {
                        originalEnd(encoding); // encoding is actually the callback
                    } else {
                        originalEnd(callback);
                    }
                };

                next();
            });
        },
    };
}
