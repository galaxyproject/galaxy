import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { http as mswHttp } from "msw";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useConfigStore } from "@/stores/configurationStore";
import { useUserStore } from "@/stores/userStore";

import App from "./App.vue";

vi.mock("@/app", () => ({ getGalaxyInstance: () => ({ config: { themes: {} } }) }));
vi.mock("@/components/Masthead/Masthead.vue", () => ({ default: {} }));
vi.mock("@/components/Notifications/Broadcasts/BroadcastsOverlay.vue", () => ({ default: {} }));
vi.mock("@/components/Tour/TourRunner.vue", () => ({ default: {} }));
vi.mock("@/components/WindowManager/WindowManagerWindow.vue", () => ({ default: {} }));

const { server, http } = useServerMock();

beforeEach(() => {
    server.use(http.get("/api/configuration", () => HttpResponse.json({})));
});

function mountApp() {
    const localVue = getLocalVue();
    const router = injectTestRouter(localVue);
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);
    return { pinia, localVue, router };
}

afterEach(() => {
    window.onbeforeunload = null;
});

it("displays a rejected user load and clears the error after retry", async () => {
    const { pinia, localVue, router } = mountApp();
    const user = useUserStore();
    vi.mocked(user.loadUser).mockRejectedValueOnce(new TypeError("Failed to fetch")).mockResolvedValue(undefined);
    const wrapper = shallowMount(App, { localVue, router, pinia });
    await flushPromises();

    expect(wrapper.find("#startup-load-error").text()).toContain("Unable to load your user data: Failed to fetch");
    await wrapper.find("#startup-load-error button").trigger("click");
    await flushPromises();
    expect(user.loadUser).toHaveBeenCalledTimes(2);
    expect(wrapper.find("#startup-load-error").exists()).toBe(false);
    wrapper.destroy();
});

it("displays a configuration load failure and retries only the configuration", async () => {
    server.use(mswHttp.get("/api/configuration", () => HttpResponse.error()));
    const { pinia, localVue, router } = mountApp();
    const config = useConfigStore();
    const user = useUserStore();
    const wrapper = shallowMount(App, { localVue, router, pinia });
    await flushPromises();

    expect(wrapper.find("#startup-load-error").text()).toContain(
        "Unable to load the Galaxy configuration: Failed to fetch",
    );
    await wrapper.find("#startup-load-error button").trigger("click");
    expect(config.loadConfig).toHaveBeenCalledOnce();
    expect(user.loadUser).toHaveBeenCalledOnce();
    wrapper.destroy();
});
