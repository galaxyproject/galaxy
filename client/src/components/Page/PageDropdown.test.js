import PageDropdown from "./PageDropdown";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";

import "jest-location-mock";

const localVue = getLocalVue(true);

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
    let wrapper;

    describe("navigation on owned pages", () => {
        beforeEach(async () => {
            const propsData = {
                root: "/rootprefix/",
                page: PAGE_DATA_OWNED,
            };
            wrapper = shallowMount(PageDropdown, {
                propsData,
                localVue,
            });
        });

        it("should create a page when create is clicked", async () => {
            await wrapper.find(".page-dropdown").trigger("click");
        });

        it("should show page title", async () => {
            const titleWrapper = await wrapper.find(".page-title");
            expect(titleWrapper.text()).toBe("My Page Title");
        });

        it("should should decorate dropdown with page ID for automation", async () => {
            const linkWrapper = await wrapper.find("[data-page-dropdown='page1235']");
            expect(linkWrapper.exists()).toBeTruthy();
        });

        it("should have a 'Share' option", async () => {
            expect(wrapper.find(".dropdown-menu .dropdown-item-share").exists()).toBeTruthy();
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
            });
        });

        it("should not have a 'Share' option", async () => {
            expect(wrapper.find(".dropdown-menu  dropdown-item-share").exists()).toBeFalsy();
        });
    });

    describe("clicking page deletion", () => {
        let axiosMock;
        let confirmRequest;

        async function mountAndDelete() {
            const propsData = {
                root: "/rootprefixdelete/",
                page: PAGE_DATA_OWNED,
            };
            wrapper = shallowMount(PageDropdown, {
                propsData,
                localVue,
            });
            await wrapper.vm.onDelete();
            await flushPromises();
        }

        beforeEach(async () => {
            axiosMock = new MockAdapter(axios);
            confirmRequest = true;
            global.confirm = jest.fn(() => confirmRequest);
            axiosMock.onDelete("rootprefixdelete/api/pages/page1235").reply(202, "deleted...");
        });

        afterEach(() => {
            axiosMock.restore();
        });

        it("should confirm with localized deletion message", async () => {
            await mountAndDelete();
            expect(global.confirm).toHaveBeenCalledWith(expect.toBeLocalized());
        });

        it("should fire deletion API request upon confirmation", async () => {
            await mountAndDelete();
            const emitted = wrapper.emitted();
            expect(emitted["onRemove"][0][0]).toEqual("page1235");
            expect(emitted["onSuccess"][0][0]).toEqual("deleted...");
        });

        it("should not fire deletion API request if not confirmed", async () => {
            confirmRequest = false;
            await mountAndDelete();
            const emitted = wrapper.emitted();
            expect(emitted["onRemove"]).toBeFalsy();
            expect(emitted["onSuccess"]).toBeFalsy();
        });
    });
});
