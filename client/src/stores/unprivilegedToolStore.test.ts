import { getFakeAnonymousUser, getFakeRegisteredUser } from "@tests/test-data";
import flushPromises from "flush-promises";
import { http as mswHttp } from "msw";
import { createPinia, disposePinia, setActivePinia } from "pinia";
import { beforeEach, expect, it, onTestFinished, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { Toast } from "@/composables/toast";
import { useUnprivilegedToolStore } from "@/stores/unprivilegedToolStore";
import { useUserStore } from "@/stores/userStore";

vi.mock("@/composables/toast");

const { server, http } = useServerMock();

const FAILURES = {
    network: () => HttpResponse.error(),
    forbidden: () => HttpResponse.json({ err_code: 403002, err_msg: "Forbidden" }, { status: 403 }),
    server: () => HttpResponse.json({ err_code: 500001, err_msg: "Internal error" }, { status: 500 }),
};

let pinia: ReturnType<typeof createPinia>;

beforeEach(() => {
    const ownedPinia = createPinia();
    pinia = ownedPinia;
    setActivePinia(ownedPinia);
    onTestFinished(() => disposePinia(ownedPinia));
    vi.mocked(Toast.error).mockClear();
});

it.each([
    ["network", true],
    ["forbidden", false],
    ["server", true],
] as const)("loads again after a %s failure, reporting it: %s", async (failure, reported) => {
    useUserStore(pinia).setCurrentUser(getFakeRegisteredUser());
    let failedRequests = 0;
    server.use(
        mswHttp.get("/api/unprivileged_tools", () => {
            failedRequests += 1;
            return FAILURES[failure]();
        }),
    );
    const store = useUnprivilegedToolStore(pinia);
    await vi.waitFor(() => expect(failedRequests).toBe(1));
    await flushPromises();
    expect(store.canUseUnprivilegedTools).toBe(false);
    expect(store.isLoaded).toBe(false);
    if (reported) {
        expect(Toast.error).toHaveBeenCalledWith(expect.any(String), "Failed to check access to custom tools");
    } else {
        expect(Toast.error).not.toHaveBeenCalled();
    }

    server.use(http.get("/api/unprivileged_tools", () => HttpResponse.json([])));
    await store.load();
    expect(store.isLoaded).toBe(true);
    expect(store.canUseUnprivilegedTools).toBe(true);
});

it("does not query custom tools for an anonymous user", async () => {
    let requests = 0;
    server.use(
        mswHttp.get("/api/unprivileged_tools", () => {
            requests += 1;
            return HttpResponse.json([]);
        }),
    );
    const userStore = useUserStore(pinia);
    userStore.currentUser = getFakeAnonymousUser();
    const store = useUnprivilegedToolStore(pinia);
    await store.load(true);
    await flushPromises();

    expect(requests).toBe(0);
    expect(store.canUseUnprivilegedTools).toBe(false);
});

it("loads custom tools once the registered user is known", async () => {
    let requests = 0;
    server.use(
        mswHttp.get("/api/unprivileged_tools", () => {
            requests += 1;
            return HttpResponse.json([]);
        }),
    );
    const store = useUnprivilegedToolStore(pinia);
    await flushPromises();
    expect(requests).toBe(0);

    useUserStore(pinia).setCurrentUser(getFakeRegisteredUser());
    await vi.waitFor(() => expect(store.canUseUnprivilegedTools).toBe(true));
    expect(requests).toBe(1);
});
