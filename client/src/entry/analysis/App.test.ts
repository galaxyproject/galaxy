import { createTestingPinia } from "@pinia/testing";
import { createTestRouter, getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { http as mswHttp } from "msw";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useConfigStore } from "@/stores/configurationStore";
import { useEntryPointStore } from "@/stores/entryPointStore";
import { useHistoryStore } from "@/stores/historyStore";
import { useNotificationsStore } from "@/stores/notificationsStore";
import { useTourStore } from "@/stores/tourStore";
import { useUserStore } from "@/stores/userStore";
import { useWindowManagerStore } from "@/stores/windowManagerStore";

import App from "./App.vue";

const galaxy = vi.hoisted(() => ({ instance: {} as Record<string, any> }));
vi.mock("@/app", () => ({ getGalaxyInstance: () => galaxy.instance }));
vi.mock("@/components/Masthead/Masthead.vue", () => ({ default: {} }));
vi.mock("@/components/Notifications/Broadcasts/BroadcastsOverlay.vue", () => ({ default: {} }));
vi.mock("@/components/Tour/TourRunner.vue", () => ({ default: {} }));
vi.mock("@/components/WindowManager/WindowManagerWindow.vue", () => ({ default: {} }));

const { server, http } = useServerMock();

beforeEach(() => {
    galaxy.instance = { config: { themes: {} } };
    server.use(http.get("/api/configuration", () => HttpResponse.json({})));
});

function mountApp() {
    const localVue = getLocalVue();
    const router = createTestRouter([{ path: "/tours/:tourId", component: { render: () => null } }]);
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
    wrapper.unmount();
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
    wrapper.unmount();
});

async function mountAt(path: string) {
    const { pinia, localVue, router } = mountApp();
    await router.push(path);
    const wrapper = shallowMount(App, { localVue, router, pinia });
    await flushPromises();
    return { wrapper, router };
}

it("applies the user's theme, falling back to the first configured theme", async () => {
    galaxy.instance.config.themes = { blue: { "--masthead-color": "blue" }, red: { "--masthead-color": "red" } };
    const { pinia, localVue, router } = mountApp();
    const user = useUserStore();
    // @ts-expect-error -- createTestingPinia makes getters writable
    user.currentTheme = "red";
    const wrapper = shallowMount(App, { localVue, router, pinia });
    await flushPromises();
    expect(wrapper.find("#app").attributes("style")).toContain("--masthead-color: red");

    // @ts-expect-error -- createTestingPinia makes getters writable
    user.currentTheme = "missing";
    await flushPromises();
    expect(wrapper.find("#app").attributes("style")).toContain("--masthead-color: blue");
    wrapper.unmount();
});

it("hides the masthead and skips window restore when hide_masthead is set", async () => {
    const { wrapper } = await mountAt("/?hide_masthead=True");
    expect(wrapper.find("#masthead").exists()).toBe(false);
    expect(useWindowManagerStore().restore).not.toHaveBeenCalled();
    expect(galaxy.instance.frame).toBeUndefined();
    wrapper.unmount();
});

it("shows the masthead and restores windows by default", async () => {
    const { wrapper } = await mountAt("/");
    const windowManagerStore = useWindowManagerStore();
    expect(wrapper.find("#masthead").exists()).toBe(true);
    expect(windowManagerStore.restore).toHaveBeenCalledOnce();
    expect(galaxy.instance.frame).toBe(windowManagerStore);
    expect(useHistoryStore().startWatchingHistory).toHaveBeenCalledOnce();
    wrapper.unmount();
});

it("starts entry point and notification watchers only when enabled", async () => {
    const { wrapper } = await mountAt("/");
    expect(useEntryPointStore().startWatchingEntryPoints).not.toHaveBeenCalled();
    expect(useNotificationsStore().startWatchingNotifications).not.toHaveBeenCalled();
    wrapper.unmount();

    galaxy.instance.config.interactivetools_enable = true;
    galaxy.instance.config.enable_notification_system = true;
    const enabled = await mountAt("/");
    expect(useEntryPointStore().startWatchingEntryPoints).toHaveBeenCalledOnce();
    expect(useNotificationsStore().startWatchingNotifications).toHaveBeenCalledOnce();
    enabled.wrapper.unmount();
});

it("does no startup work when embedded", async () => {
    const { wrapper } = await mountAt("/?embed=true");
    expect(useUserStore().$reset).toHaveBeenCalled();
    expect(useUserStore().loadUser).not.toHaveBeenCalled();
    expect(useHistoryStore().startWatchingHistory).not.toHaveBeenCalled();
    expect(useWindowManagerStore().restore).not.toHaveBeenCalled();
    expect(wrapper.find("#masthead").exists()).toBe(false);
    expect(window.onbeforeunload).toBeNull();
    wrapper.unmount();
});

it("warns before unload while windows or a confirmation need it", async () => {
    const { wrapper, router } = await mountAt("/");
    const windowManagerStore = useWindowManagerStore();
    const beforeUnload = () => (window.onbeforeunload as () => string | undefined)();
    expect(beforeUnload()).toBeUndefined();

    vi.mocked(windowManagerStore.beforeUnload).mockReturnValue(true);
    expect(beforeUnload()).toEqual("Are you sure you want to leave the page?");
    vi.mocked(windowManagerStore.beforeUnload).mockReturnValue(false);

    wrapper.findComponent({ name: "RouterView" }).vm.$emit("update:confirmation", true);
    await flushPromises();
    expect((router as unknown as { confirmation: unknown }).confirmation).toBe(true);
    expect(beforeUnload()).toEqual("Are you sure you want to leave the page?");

    await router.push("/other");
    await flushPromises();
    expect((router as unknown as { confirmation: unknown }).confirmation).toBeNull();
    expect(beforeUnload()).toBeUndefined();
    wrapper.unmount();
});

it("starts the tour named by a tour route", async () => {
    const { wrapper } = await mountAt("/tours/core.galaxy_ui");
    expect(useTourStore().setTour).toHaveBeenCalledWith("core.galaxy_ui");
    wrapper.unmount();
});

it("shows the inactivity warning for an inactive user when activation is on", async () => {
    galaxy.instance.config.user_activation_on = true;
    galaxy.instance.config.inactivity_box_content = "Please verify your email.";
    galaxy.instance.user = { id: "user-id", get: (key: string) => (key === "active" ? false : undefined) };
    const { wrapper } = await mountAt("/");
    expect(wrapper.find("#inactivebox").text()).toContain("Please verify your email.");
    wrapper.unmount();
});
