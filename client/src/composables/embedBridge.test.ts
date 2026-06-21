import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, test, vi } from "vitest";
import { ref } from "vue";

import { resolveEmbedTargetOrigin, shouldInterceptLink, useEmbedBridge } from "./embedBridge";

const ORIGIN = "https://orbit.example";

describe("resolveEmbedTargetOrigin", () => {
    test("prefers the explicit origin", () => {
        const win = { location: { ancestorOrigins: ["https://other.example"] } } as unknown as Window;
        expect(resolveEmbedTargetOrigin(win, ORIGIN)).toBe(ORIGIN);
    });

    test("falls back to the parent ancestor origin", () => {
        const win = { location: { ancestorOrigins: [ORIGIN] } } as unknown as Window;
        expect(resolveEmbedTargetOrigin(win)).toBe(ORIGIN);
    });

    test("returns null when neither is known (never '*')", () => {
        const win = { location: { ancestorOrigins: undefined } } as unknown as Window;
        expect(resolveEmbedTargetOrigin(win)).toBeNull();
    });
});

describe("shouldInterceptLink", () => {
    test.each([
        ["/datasets/123", true],
        ["https://example.org/x", true],
        ["#in-page", false],
        ["javascript:void(0)", false],
        ["", false],
        [null, false],
        [undefined, false],
    ])("shouldInterceptLink(%s) === %s", (href, expected) => {
        expect(shouldInterceptLink(href as string | null | undefined)).toBe(expected);
    });
});

interface MockWinOptions {
    ancestorOrigins?: string[];
    resizeObserver?: boolean;
}

function makeMockWin(options: MockWinOptions = {}) {
    const postMessage = vi.fn();
    const parent = { postMessage };
    let resizeCb: (() => void) | undefined;
    const win = {
        parent,
        location: { ancestorOrigins: options.ancestorOrigins },
        ResizeObserver: options.resizeObserver
            ? class {
                  constructor(cb: () => void) {
                      resizeCb = cb;
                  }
                  observe() {
                      resizeCb?.();
                  }
                  disconnect() {}
              }
            : undefined,
    } as unknown as Window;
    return { win, postMessage };
}

function mountBridge(opts: {
    enabled: boolean;
    win: Window;
    root: HTMLElement;
    title?: string;
    explicitOrigin?: string;
}) {
    const title = ref<string | undefined>(opts.title);
    const rootRef = ref<HTMLElement | undefined>(opts.root);
    const wrapper = mount({
        template: "<div />",
        setup() {
            useEmbedBridge({
                enabled: opts.enabled,
                pageId: "p1",
                title,
                root: rootRef,
                explicitOrigin: opts.explicitOrigin,
                win: opts.win,
            });
        },
    });
    return { wrapper, title };
}

describe("useEmbedBridge", () => {
    afterEach(() => {
        document.body.innerHTML = "";
        vi.clearAllMocks();
    });

    test("posts ready and title on mount, origin-restricted", () => {
        const root = document.createElement("div");
        document.body.appendChild(root);
        const { win, postMessage } = makeMockWin({ ancestorOrigins: [ORIGIN] });

        const { wrapper } = mountBridge({ enabled: true, win, root, title: "My Page" });

        expect(postMessage).toHaveBeenCalledWith({ type: "galaxy-embed:ready", pageId: "p1" }, ORIGIN);
        expect(postMessage).toHaveBeenCalledWith({ type: "galaxy-embed:title", title: "My Page" }, ORIGIN);
        wrapper.destroy();
    });

    test("does nothing when disabled", () => {
        const root = document.createElement("div");
        document.body.appendChild(root);
        const { win, postMessage } = makeMockWin({ ancestorOrigins: [ORIGIN] });

        const { wrapper } = mountBridge({ enabled: false, win, root, title: "X" });

        expect(postMessage).not.toHaveBeenCalled();
        wrapper.destroy();
    });

    test("sends nothing when no target origin can be resolved", () => {
        const root = document.createElement("div");
        document.body.appendChild(root);
        const { win, postMessage } = makeMockWin({ ancestorOrigins: undefined });

        const { wrapper } = mountBridge({ enabled: true, win, root, title: "X" });

        expect(postMessage).not.toHaveBeenCalled();
        wrapper.destroy();
    });

    test("intercepts in-iframe link clicks and routes them to the parent", () => {
        const root = document.createElement("div");
        const anchor = document.createElement("a");
        anchor.setAttribute("href", "/datasets/123");
        root.appendChild(anchor);
        document.body.appendChild(root);
        const { win, postMessage } = makeMockWin({ ancestorOrigins: [ORIGIN] });

        const { wrapper } = mountBridge({ enabled: true, win, root });

        const event = new MouseEvent("click", { bubbles: true, cancelable: true });
        anchor.dispatchEvent(event);

        expect(event.defaultPrevented).toBe(true);
        expect(postMessage).toHaveBeenCalledWith(
            expect.objectContaining({ type: "galaxy-embed:navigate", href: expect.stringContaining("/datasets/123") }),
            ORIGIN,
        );
        wrapper.destroy();
    });

    test("leaves in-page anchors alone", () => {
        const root = document.createElement("div");
        const anchor = document.createElement("a");
        anchor.setAttribute("href", "#section");
        root.appendChild(anchor);
        document.body.appendChild(root);
        const { win, postMessage } = makeMockWin({ ancestorOrigins: [ORIGIN] });

        const { wrapper } = mountBridge({ enabled: true, win, root });

        const event = new MouseEvent("click", { bubbles: true, cancelable: true });
        anchor.dispatchEvent(event);

        expect(event.defaultPrevented).toBe(false);
        const navigateCalls = postMessage.mock.calls.filter((c) => c[0]?.type === "galaxy-embed:navigate");
        expect(navigateCalls).toHaveLength(0);
        wrapper.destroy();
    });

    test("emits height from a ResizeObserver when available", () => {
        const root = document.createElement("div");
        document.body.appendChild(root);
        const { win, postMessage } = makeMockWin({ ancestorOrigins: [ORIGIN], resizeObserver: true });

        const { wrapper } = mountBridge({ enabled: true, win, root });

        const heightCalls = postMessage.mock.calls.filter((c) => c[0]?.type === "galaxy-embed:height");
        expect(heightCalls.length).toBeGreaterThan(0);
        expect(heightCalls[0]?.[1]).toBe(ORIGIN);
        wrapper.destroy();
    });

    test("re-emits title when it changes", async () => {
        const root = document.createElement("div");
        document.body.appendChild(root);
        const { win, postMessage } = makeMockWin({ ancestorOrigins: [ORIGIN] });

        const { wrapper, title } = mountBridge({ enabled: true, win, root, title: "First" });
        postMessage.mockClear();

        title.value = "Second";
        await wrapper.vm.$nextTick();

        expect(postMessage).toHaveBeenCalledWith({ type: "galaxy-embed:title", title: "Second" }, ORIGIN);
        wrapper.destroy();
    });
});
