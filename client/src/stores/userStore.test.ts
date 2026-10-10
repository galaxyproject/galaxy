import { getFakeRegisteredUser } from "@tests/test-data";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { useUserStore } from "@/stores/userStore";

const { server, http } = useServerMock();

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

    describe("getDecodedId", () => {
        let callCount = 0;

        beforeEach(() => {
            server.use(
                http.get("/api/configuration/decode/{encoded_id}", ({ response }) => {
                    callCount++;
                    return response(200).json({ decoded_id: 123 });
                }),
            );
        });
        afterEach(() => {
            callCount = 0;
        });

        it("returns null and does not fetch for a non-admin user", async () => {
            const userStore = useUserStore();
            userStore.currentUser = getFakeRegisteredUser({ is_admin: false });

            expect(userStore.getDecodedId("abc")).toBeNull();
            await flushPromises();
            expect(callCount).toBe(0);
        });

        it("decodes and caches the id for an admin user", async () => {
            const userStore = useUserStore();
            userStore.currentUser = getFakeRegisteredUser({ is_admin: true });

            expect(userStore.getDecodedId("abc")).toBeNull(); // not yet resolved
            await flushPromises();
            expect(callCount).toBe(1);
            expect(userStore.getDecodedId("abc")).toBe(123);

            // Second read for the same id should hit the cache, not trigger another fetch
            await flushPromises();
            expect(callCount).toBe(1);
        });

        it("retries once the current user becomes known, instead of setting the ID prematurely", async () => {
            const userStore = useUserStore();
            // currentUser starts as `null` (not yet loaded), `isAdmin = false`, but this
            // must not be treated as a confirmed "not admin" and cached as such.
            expect(userStore.currentUser).toBeNull();
            expect(userStore.getDecodedId("abc")).toBeNull();
            await flushPromises();
            expect(callCount).toBe(0); // never fetched while the user is unknown

            // The user loads in and turns out to be an admin.
            userStore.currentUser = getFakeRegisteredUser({ is_admin: true });
            expect(userStore.getDecodedId("abc")).toBeNull(); // not yet resolved
            await flushPromises();
            expect(callCount).toBe(1);
            expect(userStore.getDecodedId("abc")).toBe(123);
        });

        it("clears cached decoded ids on $reset so a new user doesn't see a stale result", async () => {
            const userStore = useUserStore();
            userStore.currentUser = getFakeRegisteredUser({ is_admin: true });
            userStore.getDecodedId("abc");
            await flushPromises();
            expect(userStore.getDecodedId("abc")).toBe(123);

            userStore.$reset();

            expect(userStore.getDecodedId("abc")).toBeNull();
        });
    });
});
