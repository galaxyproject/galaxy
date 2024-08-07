/* global globalThis */

/**
 * @note The block below contains polyfills for Node.js globals
 * required for Jest to function when running JSDOM tests.
 * These HAVE to be require's and HAVE to be in this exact
 * order, since "undici" depends on the "TextEncoder" global API.
 *
 * Consider migrating to a more modern test runner if
 * you don't want to deal with this.
 */

// https://mswjs.io/docs/migrations/1.x-to-2.x#frequent-issues

const { TextDecoder, TextEncoder, ReadableStream } = require("node:util");
const { clearImmediate } = require("node:timers");

Object.defineProperties(globalThis, {
    TextDecoder: { value: TextDecoder },
    TextEncoder: { value: TextEncoder },
    ReadableStream: { value: ReadableStream },
    clearImmediate: { value: clearImmediate },
});

const { Blob, File } = require("node:buffer");

Object.defineProperties(globalThis, {
    Blob: { value: Blob },
    File: { value: File },
});
