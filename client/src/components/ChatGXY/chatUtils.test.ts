import { describe, expect, it, vi } from "vitest";

import { generateId, scrollToBottom } from "./chatUtils";

describe("chatUtils", () => {
    describe("generateId", () => {
        it("returns a string starting with 'msg-'", () => {
            expect(generateId()).toMatch(/^msg-/);
        });

        it("includes a timestamp portion", () => {
            const before = Date.now();
            const id = generateId();
            const after = Date.now();

            // Extract timestamp from "msg-{timestamp}-{random}"
            const parts = id.split("-");
            const timestamp = parseInt(parts[1]!, 10);
            expect(timestamp).toBeGreaterThanOrEqual(before);
            expect(timestamp).toBeLessThanOrEqual(after);
        });

        it("generates unique ids", () => {
            const ids = new Set(Array.from({ length: 100 }, () => generateId()));
            expect(ids.size).toBe(100);
        });
    });

    describe("scrollToBottom", () => {
        it("calls scrollTo with scrollHeight on the element", () => {
            const el = {
                scrollHeight: 500,
                scrollTo: vi.fn(),
            } as unknown as HTMLElement;

            scrollToBottom(el);

            expect(el.scrollTo).toHaveBeenCalledWith({
                top: 500,
                behavior: "auto",
            });
        });

        it("does nothing when container is undefined", () => {
            // Should not throw
            scrollToBottom(undefined);
        });
    });
});
