import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue } from "@tests/vitest/helpers";
import { setupMockConfig } from "@tests/vitest/mockConfig";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { PiniaVuePlugin } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { WindowManager } from "@/entry/analysis/window-manager";
import { useUserStore } from "@/stores/userStore";

import { loadMastheadWebhooks } from "./_webhooks";

import Masthead from "./Masthead.vue";

vi.mock("app");
vi.mock("./_webhooks");
vi.mock("vue-router", () => ({
    useRoute: vi.fn(() => ({ name: "Home" })),
    useRouter: vi.fn(),
}));

const currentUser = getFakeRegisteredUser();

setupMockConfig({});

describe("Masthead.vue", () => {
    let wrapper;
    let localVue;
    let windowManager;
    let testPinia;

    function stubLoadWebhooks(items) {
        items.push({
            id: "extension",
            title: "Extension Point",
            url: "extension_url",
        });
    }

    loadMastheadWebhooks.mockImplementation(stubLoadWebhooks);

    beforeEach(async () => {
        localVue = getLocalVue();
        localVue.use(PiniaVuePlugin);
        testPinia = createTestingPinia({ createSpy: vi.fn });

        windowManager = new WindowManager({});
        const windowTab = windowManager.getTab();

        const userStore = useUserStore();
        userStore.currentUser = currentUser;

        wrapper = mount(Masthead, {
            props: {
                windowTab,
            },
            global: localVue,
            pinia: testPinia,
        });
        await flushPromises();
    });

    it("should render simple tab item links", () => {
        expect(wrapper.findAll("li.nav-item").length).toBe(4);
        // Ensure specified link title respected.
        expect(wrapper.find("#help").text()).toBe("Support, Contact, and Community");
        expect(wrapper.find("#help a").attributes("href")).toBe("/about");
    });

    it("should display window manager button", async () => {
        expect(wrapper.find("#enable-window-manager a svg").exists()).toBe(true);
        expect(windowManager.active).toBe(false);
        await wrapper.find("#enable-window-manager a").trigger("click");
        expect(windowManager.active).toBe(true);
    });

    it("should load webhooks on creation", async () => {
        expect(wrapper.find("#extension a").text()).toBe("Extension Point");
    });
});
