import { describe, expect, it, vi } from "vitest";

import { generateId, scrollToBottom } from "./utilities";

describe("ChatGXY utilities", () => {
    describe("generateId", () => {
        it("generates unique ids", () => {
            const ids = new Set(Array.from({ length: 100 }, () => generateId()));
            expect(ids.size).toBe(100);
        });
    });

    describe("scrollToBottom", () => {
        it("scrolls element without error", () => {
            const el = { scrollHeight: 500, scrollTo: vi.fn() } as unknown as HTMLElement;
            scrollToBottom(el);
            expect(el.scrollTo).toHaveBeenCalled();
        });

        it("does nothing when container is undefined", () => {
            scrollToBottom(undefined);
        });
    });
});
