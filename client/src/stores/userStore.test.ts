import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { useUserStore } from "@/stores/userStore";

describe("userStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });
    afterEach(() => {
        const userStore = useUserStore();
        userStore.$reset();
    });

    describe("addRecentTool", () => {
        it("adds tools to the front, deduplicates, and ignores empty ids", () => {
            const userStore = useUserStore();

            userStore.addRecentTool("");
            expect(userStore.recentTools).toEqual([]);

            userStore.addRecentTool("tool_a");
            userStore.addRecentTool("tool_b");
            userStore.addRecentTool("tool_c");
            expect(userStore.recentTools).toEqual(["tool_c", "tool_b", "tool_a"]);

            // re-adding an existing tool moves it to front without duplicating
            userStore.addRecentTool("tool_a");
            expect(userStore.recentTools).toEqual(["tool_a", "tool_c", "tool_b"]);
        });

        it("drops the oldest tool when the limit is reached", () => {
            const userStore = useUserStore();
            for (let i = 0; i < 10; i++) {
                userStore.addRecentTool(`tool_${i}`);
            }
            expect(userStore.recentTools).toHaveLength(10);
            expect(userStore.recentTools[0]).toBe("tool_9");
            expect(userStore.recentTools[9]).toBe("tool_0");

            userStore.addRecentTool("tool_new");
            expect(userStore.recentTools).toHaveLength(10);
            expect(userStore.recentTools[0]).toBe("tool_new");
            expect(userStore.recentTools).not.toContain("tool_0");
        });
    });

    describe("clearRecentTools", () => {
        it("clears all recent tools", () => {
            const userStore = useUserStore();
            userStore.addRecentTool("tool_a");
            userStore.addRecentTool("tool_b");
            expect(userStore.recentTools).toHaveLength(2);

            userStore.clearRecentTools();
            expect(userStore.recentTools).toEqual([]);
        });
    });
});
