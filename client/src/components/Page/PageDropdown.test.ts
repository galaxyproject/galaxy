import { expect, jest } from "@jest/globals";

import { mount, shallowMount, createWrapper } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import { PiniaVuePlugin, createPinia } from "pinia";
import { createTestingPinia } from "@pinia/testing";
import { mockFetcher } from "@/schema/__mocks__";
import { useUserStore } from "@/stores/userStore";

import PageDropdown from "./PageDropdown.vue";

import "jest-location-mock";

jest.mock("@/schema");

const waitRAF = () => new Promise((resolve) => requestAnimationFrame(resolve));

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
            userStore.currentUser = { email: "my@email", id: "1", tags_used: [], isAnonymous: false };
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

    describe("clicking page deletion on owned page", () => {
        const pinia = createPinia();

        async function mountAndDelete() {
            const propsData = {
                root: "/rootprefixdelete/",
                page: PAGE_DATA_OWNED,
            };
            wrapper = mount(PageDropdown, {
                propsData,
                localVue,
                pinia: pinia,
                stubs: {
                    transition: false,
                },
            });
            const userStore = useUserStore();
            userStore.currentUser = { email: "my@email", id: "1", tags_used: [], isAnonymous: false };
            wrapper.find(".page-dropdown").trigger("click");
            await wrapper.vm.$nextTick();
            wrapper.find(".dropdown-item-delete").trigger("click");
            // this is here because b-modal is lazy loading and portalling
            // see https://github.com/bootstrap-vue/bootstrap-vue/blob/dev/src/components/modal/modal.spec.js#L233
            await wrapper.vm.$nextTick();
            await waitRAF();
            await wrapper.vm.$nextTick();
            await waitRAF();
            await wrapper.vm.$nextTick();
            await waitRAF();
            const foot: any = document.getElementById("delete-page-modal-page1235___BV_modal_footer_");
            createWrapper(foot).find(".btn-primary").trigger("click");
            await wrapper.vm.$nextTick();
            await waitRAF();
            await wrapper.vm.$nextTick();
            await waitRAF();
        }

        afterEach(() => {
            mockFetcher.clearMocks();
        });

        it("should fire deletion API request upon confirmation", async () => {
            mockFetcher.path("/api/pages/{id}").method("delete").mock({ status: 204 });
            await mountAndDelete();
            const emitted = wrapper.emitted();
            expect(emitted["onRemove"][0][0]).toEqual("page1235");
            expect(emitted["onSuccess"]).toBeTruthy();
        });

        it("should not fire deletion API request if not confirmed", async () => {
            await mountAndDelete();
            const emitted = wrapper.emitted();
            expect(emitted["onRemove"]).toBeFalsy();
            expect(emitted["onSuccess"]).toBeFalsy();
        });

        it("should emit an error on API fail", async () => {
            mockFetcher
                .path("/api/pages/{id}")
                .method("delete")
                .mock(() => {
                    throw Error("mock error");
                });
            await mountAndDelete();
            const emitted = wrapper.emitted();
            expect(emitted["onError"]).toBeTruthy();
        });
    });
});
