import { http as mswHttp } from "msw";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { Toast } from "@/composables/toast";
import { useConfigStore } from "@/stores/configurationStore";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

vi.mock("@/composables/toast");

const { server, http } = useServerMock();
const anonymousUser = { nice_total_disk_usage: "0 bytes", total_disk_usage: 0 };

beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    server.use(http.get("/api/configuration", () => HttpResponse.json({})));
});

describe("startup request failures", () => {
    it("retries a failed user request while sharing and caching successful loads", async () => {
        const request = vi
            .fn()
            .mockReturnValueOnce(HttpResponse.error())
            .mockImplementation(() => HttpResponse.json(anonymousUser));
        server.use(http.get("/api/users/{user_id}", request));
        const store = useUserStore();

        const results = await Promise.allSettled([store.loadUser(false), store.loadUser(false)]);
        expect(results.map((result) => result.status)).toEqual(["rejected", "rejected"]);
        expect(request).toHaveBeenCalledTimes(1);

        await Promise.all([store.loadUser(false), store.loadUser(false)]);
        await store.loadUser(false);
        expect(request).toHaveBeenCalledTimes(2);
        expect(store.currentUser).not.toBeNull();
    });

    it("clears history loading after a count failure and allows user initialization to retry", async () => {
        server.use(http.get("/api/users/{user_id}", () => HttpResponse.json(anonymousUser)));
        const count = vi
            .fn()
            .mockReturnValueOnce(HttpResponse.error())
            .mockImplementation(() => HttpResponse.json(0));
        server.use(http.get("/api/histories/count", count));
        const user = useUserStore();
        const history = useHistoryStore();

        await expect(user.loadUser()).rejects.toThrow("Failed to fetch");
        expect(history.historiesLoading).toBe(false);

        await user.loadUser();
        expect(count).toHaveBeenCalledTimes(2);
        expect(history.historiesLoading).toBe(false);
    });

    it.each(["network", "http"])("handles a %s configuration failure and permits retry", async (failure) => {
        server.use(
            mswHttp.get("/api/configuration", () =>
                failure === "network"
                    ? HttpResponse.error()
                    : HttpResponse.json({ err_code: 503, err_msg: "Unavailable" }, { status: 503 }),
            ),
        );
        const store = useConfigStore();
        await vi.waitFor(() => expect(Toast.error).toHaveBeenCalledOnce());
        expect(Toast.error).toHaveBeenCalledWith(expect.any(String), "Unable to load Galaxy configuration");
        expect(store.isLoaded).toBe(false);

        server.use(http.get("/api/configuration", () => HttpResponse.json({ brand: "Galaxy" })));
        await store.loadConfig();
        expect(store.isLoaded).toBe(true);
        expect(store.config.brand).toBe("Galaxy");
    });
});
