import { http as mswHttp } from "msw";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { Toast } from "@/composables/toast";
import { useConfigStore } from "@/stores/configurationStore";

vi.mock("@/composables/toast");

const { server, http } = useServerMock();

beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
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
