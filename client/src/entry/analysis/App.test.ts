import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { expect, it, vi } from "vitest";

import { useUserStore } from "@/stores/userStore";

import App from "./App.vue";

vi.mock("@/app", () => ({ getGalaxyInstance: () => ({ config: { themes: {} } }) }));
vi.mock("@/components/Masthead/Masthead.vue", () => ({ default: {} }));
vi.mock("@/components/Notifications/Broadcasts/BroadcastsOverlay.vue", () => ({ default: {} }));
vi.mock("@/components/Tour/TourRunner.vue", () => ({ default: {} }));
vi.mock("@/components/WindowManager/WindowManagerWindow.vue", () => ({ default: {} }));

it("displays a rejected startup load and clears the error after retry", async () => {
    const localVue = getLocalVue();
    const router = injectTestRouter(localVue);
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);
    const user = useUserStore();
    vi.mocked(user.loadUser).mockRejectedValueOnce(new TypeError("Failed to fetch")).mockResolvedValue(undefined);
    const wrapper = shallowMount(App, { localVue, router, pinia });
    await flushPromises();

    expect(wrapper.find("#user-load-error").text()).toContain("Failed to fetch");
    await wrapper.find("#user-load-error button").trigger("click");
    await flushPromises();
    expect(user.loadUser).toHaveBeenCalledTimes(2);
    expect(wrapper.find("#user-load-error").exists()).toBe(false);
    wrapper.destroy();
    window.onbeforeunload = null;
});
