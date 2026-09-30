import flushPromises from "flush-promises";
import { http as mswHttp } from "msw";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useUnprivilegedToolStore } from "@/stores/unprivilegedToolStore";

const { toastError } = vi.hoisted(() => ({ toastError: vi.fn() }));

vi.mock("@/composables/toast", () => ({
    useToast: () => ({ error: toastError }),
}));

const { server, http } = useServerMock();

const FAILURES = {
    network: () => HttpResponse.error(),
    forbidden: () => HttpResponse.json({ err_code: 403002, err_msg: "Forbidden" }, { status: 403 }),
    server: () => HttpResponse.json({ err_code: 500001, err_msg: "Internal error" }, { status: 500 }),
};

beforeEach(() => {
    setActivePinia(createPinia());
    toastError.mockClear();
});

it.each([
    ["network", true],
    ["forbidden", false],
    ["server", true],
] as const)("loads again after a %s failure, reporting it: %s", async (failure, reported) => {
    let failedRequests = 0;
    server.use(
        mswHttp.get("/api/unprivileged_tools", () => {
            failedRequests += 1;
            return FAILURES[failure]();
        }),
    );
    const store = useUnprivilegedToolStore();
    await vi.waitFor(() => expect(failedRequests).toBe(1));
    await flushPromises();
    expect(store.canUseUnprivilegedTools).toBe(false);
    expect(store.isLoaded).toBe(false);
    if (reported) {
        expect(toastError).toHaveBeenCalledWith(expect.any(String), "Failed to check access to custom tools");
    } else {
        expect(toastError).not.toHaveBeenCalled();
    }

    server.use(http.get("/api/unprivileged_tools", () => HttpResponse.json([])));
    await store.load();
    expect(store.isLoaded).toBe(true);
    expect(store.canUseUnprivilegedTools).toBe(true);
});
