import { createTestingPinia } from "@pinia/testing";
import { createTestRouter, getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { http as mswHttp } from "msw";
import { disposePinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, expect, it, onTestFinished, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useConfigStore } from "@/stores/configurationStore";
import { useEntryPointStore } from "@/stores/entryPointStore";
import { useHistoryStore } from "@/stores/historyStore";
import { useNotificationsStore } from "@/stores/notificationsStore";
import { useTourStore } from "@/stores/tourStore";
import { useUserStore } from "@/stores/userStore";
import { useWindowManagerStore } from "@/stores/windowManagerStore";

import App from "./App.vue";

interface GalaxyFixture {
    config: {
        themes: Record<string, Record<string, string>>;
        interactivetools_enable?: boolean;
        enable_notification_system?: boolean;
        user_activation_on?: boolean;
        inactivity_box_content?: string;
    };
    frame?: ReturnType<typeof useWindowManagerStore>;
    user?: { id: string; get: (key: string) => boolean | undefined };
}

type ConfirmableRouter = ReturnType<typeof createTestRouter> & { confirmation?: boolean | null };

const galaxy = vi.hoisted(() => ({ instance: { config: { themes: {} } } as GalaxyFixture }));
vi.mock("@/app", () => ({ getGalaxyInstance: () => galaxy.instance }));
vi.mock("@/components/Masthead/Masthead.vue", () => ({ default: {} }));
vi.mock("@/components/Notifications/Broadcasts/BroadcastsOverlay.vue", () => ({ default: {} }));
vi.mock("@/components/Tour/TourRunner.vue", () => ({ default: {} }));
vi.mock("@/components/WindowManager/WindowManagerWindow.vue", () => ({ default: {} }));

const { server, http } = useServerMock();

beforeEach(() => {
    const originalBeforeUnload = window.onbeforeunload;
    onTestFinished(() => {
        window.onbeforeunload = originalBeforeUnload;
    });
    galaxy.instance = { config: { themes: {} } };
    server.use(http.get("/api/configuration", () => HttpResponse.json({})));
});

function mountApp() {
    const localVue = getLocalVue();
    const router: ConfirmableRouter = createTestRouter([{ path: "/tours/:tourId", component: { render: () => null } }]);
    const pinia = createTestingPinia({ createSpy: vi.fn });
    onTestFinished(() => disposePinia(pinia));
    setActivePinia(pinia);
    return { pinia, global: withPlugins(localVue, pinia, router), router };
}

enableAutoUnmount(afterEach);

it("displays a rejected user load and clears the error after retry", async () => {
    const { pinia, global } = mountApp();
    const user = useUserStore(pinia);
    vi.mocked(user.loadUser).mockRejectedValueOnce(new TypeError("Failed to fetch")).mockResolvedValue(undefined);
    const wrapper = shallowMount(App, { global });
    await flushPromises();

    expect(wrapper.get("#startup-load-error").text()).toContain("Unable to load your user data: Failed to fetch");
    await wrapper.get("#startup-load-error button").trigger("click");
    await flushPromises();
    expect(user.loadUser).toHaveBeenCalledTimes(2);
    expect(wrapper.find("#startup-load-error").exists()).toBe(false);
    wrapper.unmount();
});

it("displays a configuration load failure and retries only the configuration", async () => {
    server.use(mswHttp.get("/api/configuration", () => HttpResponse.error()));
    const { pinia, global } = mountApp();
    const config = useConfigStore(pinia);
    const user = useUserStore(pinia);
    const wrapper = shallowMount(App, { global });
    await flushPromises();

    expect(wrapper.get("#startup-load-error").text()).toContain(
        "Unable to load the Galaxy configuration: Failed to fetch",
    );
    await wrapper.get("#startup-load-error button").trigger("click");
    expect(config.loadConfig).toHaveBeenCalledOnce();
    expect(user.loadUser).toHaveBeenCalledOnce();
    wrapper.unmount();
});

async function mountAt(path: string) {
    const { pinia, global, router } = mountApp();
    await router.push(path);
    const wrapper = shallowMount(App, { global });
    await flushPromises();
    return { wrapper, router, pinia };
}

it("applies the user's theme, falling back to the first configured theme", async () => {
    galaxy.instance.config.themes = { blue: { "--masthead-color": "blue" }, red: { "--masthead-color": "red" } };
    const { pinia, global } = mountApp();
    const user = useUserStore(pinia);
    // @ts-expect-error -- createTestingPinia makes getters writable
    user.currentTheme = "red";
    const wrapper = shallowMount(App, { global });
    await flushPromises();
    expect(wrapper.get("#app").attributes("style")).toContain("--masthead-color: red");

    // @ts-expect-error -- createTestingPinia makes getters writable
    user.currentTheme = "missing";
    await flushPromises();
    expect(wrapper.get("#app").attributes("style")).toContain("--masthead-color: blue");
    wrapper.unmount();
});

it("hides the masthead and skips window restore when hide_masthead is set", async () => {
    const { wrapper, pinia } = await mountAt("/?hide_masthead=True");
    expect(wrapper.find("#masthead").exists()).toBe(false);
    expect(useWindowManagerStore(pinia).restore).not.toHaveBeenCalled();
    expect(galaxy.instance.frame).toBeUndefined();
    wrapper.unmount();
});

it("shows the masthead and restores windows by default", async () => {
    const { wrapper, pinia } = await mountAt("/");
    const windowManagerStore = useWindowManagerStore(pinia);
    expect(wrapper.find("#masthead").exists()).toBe(true);
    expect(windowManagerStore.restore).toHaveBeenCalledOnce();
    expect(galaxy.instance.frame).toBe(windowManagerStore);
    expect(useHistoryStore(pinia).startWatchingHistory).toHaveBeenCalledOnce();
    wrapper.unmount();
});

it("starts entry point and notification watchers only when enabled", async () => {
    const { wrapper, pinia } = await mountAt("/");
    expect(useEntryPointStore(pinia).startWatchingEntryPoints).not.toHaveBeenCalled();
    expect(useNotificationsStore(pinia).startWatchingNotifications).not.toHaveBeenCalled();
    wrapper.unmount();

    galaxy.instance.config.interactivetools_enable = true;
    galaxy.instance.config.enable_notification_system = true;
    const enabled = await mountAt("/");
    expect(useEntryPointStore(enabled.pinia).startWatchingEntryPoints).toHaveBeenCalledOnce();
    expect(useNotificationsStore(enabled.pinia).startWatchingNotifications).toHaveBeenCalledOnce();
    enabled.wrapper.unmount();
});

it("does no startup work when embedded", async () => {
    const { wrapper, pinia } = await mountAt("/?embed=true");
    expect(useUserStore(pinia).$reset).toHaveBeenCalled();
    expect(useUserStore(pinia).loadUser).not.toHaveBeenCalled();
    expect(useHistoryStore(pinia).startWatchingHistory).not.toHaveBeenCalled();
    expect(useWindowManagerStore(pinia).restore).not.toHaveBeenCalled();
    expect(wrapper.find("#masthead").exists()).toBe(false);
    expect(window.onbeforeunload).toBeNull();
    wrapper.unmount();
});

it("warns before unload while windows or a confirmation need it", async () => {
    const { wrapper, router, pinia } = await mountAt("/");
    const windowManagerStore = useWindowManagerStore(pinia);
    const beforeUnload = () => (window.onbeforeunload as () => string | undefined)();
    expect(beforeUnload()).toBeUndefined();

    vi.mocked(windowManagerStore.beforeUnload).mockReturnValue(true);
    expect(beforeUnload()).toEqual("Are you sure you want to leave the page?");
    vi.mocked(windowManagerStore.beforeUnload).mockReturnValue(false);

    wrapper.getComponent({ name: "RouterView" }).vm.$emit("update:confirmation", true);
    await flushPromises();
    expect(router.confirmation).toBe(true);
    expect(beforeUnload()).toEqual("Are you sure you want to leave the page?");

    await router.push("/other");
    await flushPromises();
    expect(router.confirmation).toBeNull();
    expect(beforeUnload()).toBeUndefined();
    wrapper.unmount();
});

it("starts the tour named by a tour route", async () => {
    const { wrapper, pinia } = await mountAt("/tours/core.galaxy_ui");
    expect(useTourStore(pinia).setTour).toHaveBeenCalledWith("core.galaxy_ui");
    wrapper.unmount();
});

it("shows the inactivity warning for an inactive user when activation is on", async () => {
    galaxy.instance.config.user_activation_on = true;
    galaxy.instance.config.inactivity_box_content = "Please verify your email.";
    galaxy.instance.user = { id: "user-id", get: (key: string) => (key === "active" ? false : undefined) };
    const { wrapper } = await mountAt("/");
    expect(wrapper.get("#inactivebox").text()).toContain("Please verify your email.");
    wrapper.unmount();
});
