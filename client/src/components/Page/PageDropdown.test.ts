import { expect, jest } from "@jest/globals";

import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import { PiniaVuePlugin, createPinia } from "pinia";
import { createTestingPinia } from "@pinia/testing";
import { useUserStore } from "@/stores/userStore";

import PageDropdown from "./PageDropdown.vue";

import "jest-location-mock";

jest.mock("@/schema");

const localVue = getLocalVue(true);
localVue.use(PiniaVuePlugin);

const PAGE_DATA_OWNED = {
    id: "page1235",
    title: "My Page Title",
    description: "A description derived from an annotation.",
    shared: false,
};

const PAGE_DATA_SHARED = {
    id: "page1235",
    title: "My Page Title",
    description: "A description derived from an annotation.",
    shared: true,
};

describe("PageDropdown.vue", () => {
    let wrapper: any;

    function pageOptions() {
        return wrapper.findAll(".dropdown-menu .dropdown-item");
    }

    describe("navigation on owned pages", () => {
        beforeEach(async () => {
            const pinia = createPinia();
            const propsData = {
                root: "/rootprefix/",
                page: PAGE_DATA_OWNED,
            };
            wrapper = shallowMount(PageDropdown, {
                propsData,
                localVue,
                pinia: pinia,
            });
            const userStore = useUserStore();
            userStore.currentUser = { email: "my@email", id: "1", tags_used: [] };
        });

        it("should show page title", async () => {
            const titleWrapper = await wrapper.find(".page-title");
            expect(titleWrapper.text()).toBe("My Page Title");
        });

        it("should decorate dropdown with page ID for automation", async () => {
            const linkWrapper = await wrapper.find("[data-page-dropdown='page1235']");
            expect(linkWrapper.exists()).toBeTruthy();
        });

        it("should have a 'Share' option", async () => {
            expect(wrapper.find(".dropdown-menu .dropdown-item-share").exists()).toBeTruthy();
        });

        it("should provide 5 options", () => {
            expect(pageOptions().length).toBe(5);
        });
    });

    describe("navigation on shared pages", () => {
        beforeEach(async () => {
            const propsData = {
                root: "/rootprefixshared/",
                page: PAGE_DATA_SHARED,
            };
            wrapper = shallowMount(PageDropdown, {
                propsData,
                localVue,
                pinia: createTestingPinia(),
            });
        });

        it("should have the 'View' option", async () => {
            expect(wrapper.find(".dropdown-menu .dropdown-item-view").exists()).toBeTruthy();
        });

        it("should have only single option", () => {
            expect(pageOptions().length).toBe(1);
        });
    });
});
