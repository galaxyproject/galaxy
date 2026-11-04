import { getFakeRegisteredUser } from "@tests/test-data";
import flushPromises from "flush-promises";
import { delay } from "msw";
import { createPinia, setActivePinia, storeToRefs } from "pinia";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { watch } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import { useQuotaUsageStore } from "@/stores/quotaUsageStore";
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

        it("falls back to the bootstrapped Galaxy user in embedded views, where the store's user is never loaded", async () => {
            const windowWithGalaxy = window as unknown as { _galaxyInstance?: unknown };
            windowWithGalaxy._galaxyInstance = { user: { isAdmin: () => true } };
            try {
                const userStore = useUserStore();
                expect(userStore.currentUser).toBeNull();

                expect(userStore.getDecodedId("abc")).toBeNull(); // not yet resolved
                await flushPromises();
                expect(callCount).toBe(1);
                expect(userStore.getDecodedId("abc")).toBe(123);
            } finally {
                delete windowWithGalaxy._galaxyInstance;
            }
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

    describe("refreshStorageUsage", () => {
        let requested: string[];

        beforeEach(() => {
            requested = [];
            server.use(
                http.get("/api/users/{user_id}", ({ response }) => {
                    requested.push("user");
                    return response(200).json(getFakeRegisteredUser({ total_disk_usage: 2048 }));
                }),
                http.get("/api/users/{user_id}/usage", ({ response }) => {
                    requested.push("usages");
                    return response(200).json([{ quota_source_label: null, total_disk_usage: 2048 }]);
                }),
            );
        });

        it("reloads the user and the usage of every storage source once that was loaded", async () => {
            await useQuotaUsageStore().loadQuotaUsages();
            requested = [];

            await useUserStore().refreshStorageUsage();

            expect(requested.sort()).toEqual(["usages", "user"]);
            expect(useUserStore().currentUser?.total_disk_usage).toBe(2048);
        });

        it("doesn't load the usage of every storage source when nothing shows it", async () => {
            await useUserStore().refreshStorageUsage();

            expect(requested).toEqual(["user"]);
        });

        it("retries loading the usage of every storage source after that failed", async () => {
            let failing = true;
            server.use(
                http.get("/api/users/{user_id}/usage", ({ response }) => {
                    if (failing) {
                        return response("5XX").json({ err_msg: "Server error", err_code: 500 }, { status: 500 });
                    }
                    return response(200).json([{ quota_source_label: null, total_disk_usage: 2048 }]);
                }),
            );
            await useQuotaUsageStore().loadQuotaUsages();
            failing = false;

            await useUserStore().refreshStorageUsage();

            expect(useQuotaUsageStore().quotaUsages?.map((usage) => usage.totalDiskUsageInBytes)).toEqual([2048]);
        });

        it("reloads the usage of every storage source after the usage of one was loaded", async () => {
            server.use(
                http.get("/api/users/{user_id}/usage/{label}", ({ response }) =>
                    response(200).json({ quota_source_label: "scratch", total_disk_usage: 1024 }),
                ),
            );
            await useQuotaUsageStore().loadQuotaUsageForSource("scratch");
            requested = [];

            await useUserStore().refreshStorageUsage();

            expect(requested.sort()).toEqual(["usages", "user"]);
        });

        it("reloads the usage of every storage source when its first load is still running", async () => {
            const firstLoad = useQuotaUsageStore().loadQuotaUsages();

            await Promise.all([firstLoad, useUserStore().refreshStorageUsage()]);
            await flushPromises();

            expect(requested.filter((request) => request === "usages")).toEqual(["usages", "usages"]);
        });
    });

    describe("refreshUser", () => {
        it("keeps the newest user when an older request answers last", async () => {
            let requests = 0;
            server.use(
                http.get("/api/users/{user_id}", async ({ response }) => {
                    requests++;
                    if (requests === 1) {
                        await delay(50);
                        return response(200).json(getFakeRegisteredUser({ total_disk_usage: 1 }));
                    }
                    return response(200).json(getFakeRegisteredUser({ total_disk_usage: 2 }));
                }),
            );
            const userStore = useUserStore();

            const olderRefresh = userStore.refreshUser();
            await userStore.refreshUser();
            await olderRefresh;

            expect(userStore.currentUser?.total_disk_usage).toBe(2);
        });

        it("sets the user when a load answers before a later refresh", async () => {
            const responses = [
                { delayMs: 10, user: getFakeRegisteredUser({ total_disk_usage: 1 }) },
                { delayMs: 50, user: getFakeRegisteredUser({ total_disk_usage: 2 }) },
            ];
            server.use(
                http.get("/api/users/{user_id}", async ({ response }) => {
                    const { delayMs, user } = responses.shift()!;
                    await delay(delayMs);
                    return response(200).json(user);
                }),
            );
            const userStore = useUserStore();

            const firstLoad = userStore.loadUser(false);
            const refresh = userStore.refreshUser();
            await firstLoad;

            expect(userStore.currentUser?.total_disk_usage).toBe(1);
            await refresh;
        });

        it("doesn't notify the preferences' watchers when a refresh returns the same preferences", async () => {
            const preferences = { favorites: JSON.stringify({ tools: ["cat1"] }) };
            server.use(
                http.get("/api/users/{user_id}", ({ response }) =>
                    response(200).json(getFakeRegisteredUser({ preferences })),
                ),
            );
            const userStore = useUserStore();
            await userStore.refreshUser();
            const { currentFavorites } = storeToRefs(userStore);
            let notifications = 0;
            watch(currentFavorites, () => notifications++);

            await userStore.refreshUser();
            await flushPromises();

            expect(notifications).toBe(0);
        });
    });
});
