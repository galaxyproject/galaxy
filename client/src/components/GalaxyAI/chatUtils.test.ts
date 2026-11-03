import { describe, expect, it, vi } from "vitest";

import { generateId, scrollToBottom } from "./chatUtils";

describe("chatUtils", () => {
    describe("generateId", () => {
        it("generates unique ids", () => {
            const ids = new Set(Array.from({ length: 100 }, () => generateId()));
            expect(ids.size).toBe(100);
        });
    });

    describe("scrollToBottom", () => {
        it("scrolls to the full content height without animation", () => {
            const container = document.createElement("div");
            Object.defineProperty(container, "scrollHeight", { value: 500 });
            container.scrollTo = vi.fn();

            scrollToBottom(container);

            expect(container.scrollTo).toHaveBeenCalledExactlyOnceWith({ top: 500, behavior: "auto" });
        });

        it("does nothing when container is undefined", () => {
            expect(() => scrollToBottom(undefined)).not.toThrow();
        });
    });
});
