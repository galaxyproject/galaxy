import { http as mswHttp } from "msw";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useConfigStore } from "@/stores/configurationStore";

const { server, http } = useServerMock();

beforeEach(() => {
    setActivePinia(createPinia());
});

it.each(["network", "http"])("keeps a %s configuration failure and clears it on retry", async (failure) => {
    server.use(
        mswHttp.get("/api/configuration", () =>
            failure === "network"
                ? HttpResponse.error()
                : HttpResponse.json({ err_code: 503, err_msg: "Unavailable" }, { status: 503 }),
        ),
    );
    const store = useConfigStore();
    await vi.waitFor(() => expect(store.loadError).not.toBe(""));
    expect(store.isLoaded).toBe(false);

    server.use(http.get("/api/configuration", () => HttpResponse.json({ brand: "Galaxy" })));
    await store.loadConfig();
    expect(store.isLoaded).toBe(true);
    expect(store.loadError).toBe("");
    expect(store.config.brand).toBe("Galaxy");
});
