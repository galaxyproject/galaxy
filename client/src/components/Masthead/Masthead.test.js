import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { mount } from "@vue/test-utils";
import { WindowManager } from "layout/window-manager";
import { PiniaVuePlugin } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { mockFetcher } from "@/api/schema/__mocks__";
import { useUserStore } from "@/stores/userStore";

import { loadWebhookMenuItems } from "./_webhooks";

import Masthead from "./Masthead.vue";

jest.mock("app");
jest.mock("./_webhooks");
jest.mock("vue-router/composables", () => ({
    useRoute: jest.fn(() => ({ name: "Home" })),
    useRouter: jest.fn(),
}));
jest.mock("@/api/schema");

const currentUser = getFakeRegisteredUser();

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

    loadWebhookMenuItems.mockImplementation(stubLoadWebhooks);

    beforeEach(() => {
        localVue = getLocalVue();
        localVue.use(PiniaVuePlugin);
        testPinia = createTestingPinia();
        mockFetcher.path("/api/configuration").method("get").mock({ data: {} });

        windowManager = new WindowManager({});
        const windowTab = windowManager.getTab();

        const userStore = useUserStore();
        userStore.currentUser = currentUser;

        wrapper = mount(Masthead, {
            propsData: {
                windowTab,
            },
            localVue,
            pinia: testPinia,
        });
    });

    it("should render simple tab item links", () => {
        expect(wrapper.findAll("li.nav-item").length).toBe(4);
        // Ensure specified link title respected.
        expect(wrapper.find("#help").text()).toBe("Support, Contact, and Community");
        expect(wrapper.find("#help a").attributes("href")).toBe("/about");
    });

    it("should display window manager button", async () => {
        expect(wrapper.find("#enable-window-manager a span.fa-th").exists()).toBe(true);
        expect(windowManager.active).toBe(false);
        await wrapper.find("#enable-window-manager a").trigger("click");
        expect(windowManager.active).toBe(true);
    });

    it("should load webhooks on creation", async () => {
        expect(wrapper.find("#extension a").text()).toBe("Extension Point");
    });
});
