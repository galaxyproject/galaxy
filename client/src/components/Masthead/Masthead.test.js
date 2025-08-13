import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { WindowManager } from "layout/window-manager";
import { setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";
import { setupMockConfig } from "tests/jest/mockConfig";

import { useUserStore } from "@/stores/userStore";

import { loadWebhookMenuItems } from "./_webhooks";

import Masthead from "./Masthead.vue";

jest.mock("app");
jest.mock("./_webhooks");
jest.mock("vue-router", () => ({
    useRoute: jest.fn(() => ({ name: "Home" })),
    useRouter: jest.fn(),
}));

const currentUser = getFakeRegisteredUser();

setupMockConfig({});

describe("Masthead.vue", () => {
    let wrapper;
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

    beforeEach(async () => {
        const globalConfig = getLocalVue();
        testPinia = createTestingPinia();
        setActivePinia(testPinia);

        windowManager = new WindowManager({});
        const windowTab = windowManager.getTab();

        const userStore = useUserStore();
        userStore.currentUser = currentUser;

        wrapper = mount(Masthead, {
            props: {
                windowTab,
            },
            global: {
                ...globalConfig.global,
                plugins: [...globalConfig.global.plugins, testPinia],
                stubs: {
                    Icon: true,
                    MastheadItem: { 
                        template: '<li class="nav-item"><a :id="id" :href="url" class="nav-link" @click="$emit(\'click\')"><span v-if="icon" class="sr-only">{{ tooltip || id }}</span><span v-if="icon" :class="icon"></span><span v-if="toggle" class="nav-note fa fa-check"></span><span v-if="!icon">{{ title }}</span><slot></slot></a></li>',
                        props: ['id', 'url', 'icon', 'title', 'tooltip', 'target', 'toggle', 'disabled'],
                        emits: ['click']
                    },
                    MastheadDropdown: { 
                        template: '<li class="nav-item"><a :id="id" class="nav-link"><slot></slot></a></li>',
                        props: ['id', 'title', 'icon', 'tooltip', 'menu'],
                        emits: ['click']
                    },
                    QuotaMeter: { template: '<div></div>' },
                    'b-navbar': { template: '<nav role="navigation" aria-label="Main" class="justify-content-between"><slot></slot></nav>' },
                    'b-navbar-brand': { template: '<a class="ml-2 mr-2 p-0" title="homepage" aria-label="homepage"><slot></slot></a>' },
                    'b-navbar-nav': { template: '<div><slot></slot></div>' },
                },
            },
        });
        await flushPromises();
    });

    it("should render simple tab item links", () => {
        expect(wrapper.findAll("li.nav-item").length).toBe(4);
        // Ensure specified link title respected.
        expect(wrapper.find("#help .sr-only").text()).toBe("Support, Contact, and Community");
        expect(wrapper.find("#help").attributes("href")).toBe("/about");
    });

    it("should display window manager button", async () => {
        expect(wrapper.find("#enable-window-manager span.fa-th").exists()).toBe(true);
        expect(windowManager.active).toBe(false);
        await wrapper.find("#enable-window-manager").trigger("click");
        expect(windowManager.active).toBe(true);
    });

    it("should load webhooks on creation", async () => {
        expect(wrapper.find("#extension").text()).toBe("Extension Point");
    });
});
