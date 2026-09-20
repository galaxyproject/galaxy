import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import type { Pinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import PageView from "./PageView.vue";
import Heading from "@/components/Common/Heading.vue";
import PublishedItem from "@/components/Common/PublishedItem.vue";

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(() => ({
        config: ref({ enable_beta_markdown_export: false }),
        isConfigLoaded: ref(true),
    })),
}));

vi.mock("vue-router/composables", () => ({
    useRouter: vi.fn(() => ({ push: vi.fn() })),
    useRoute: vi.fn(() => ({ params: {} })),
}));

const mockUrlData = vi.fn();
vi.mock("@/utils/url", () => ({
    urlData: (...args: any[]) => mockUrlData(...args),
}));

const localVue = getLocalVue();

const PAGE_ID = "page-1";
const PAGE_DATA = {
    id: PAGE_ID,
    title: "Test Page",
    name: "Test Page",
    content: "# Hello World",
    content_format: "markdown",
    slug: "test-page",
    username: "testuser",
    model_class: "Page",
};

let pinia: Pinia;

function mountComponent(propsData: { pageId: string; embed?: boolean; displayOnly?: boolean; showHeading?: boolean }) {
    return shallowMount(PageView as object, {
        localVue,
        pinia,
        propsData,
        stubs: {
            FontAwesomeIcon: true,
            LoadingSpan: true,
            Markdown: true,
            PageHtml: true,
        },
    });
}

describe("PageView", () => {
    beforeEach(() => {
        pinia = createTestingPinia({ createSpy: vi.fn });
        vi.clearAllMocks();
        mockUrlData.mockResolvedValue(PAGE_DATA);
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe("default mode (published page with chrome)", () => {
        it("renders PublishedItem wrapper", async () => {
            const wrapper = mountComponent({ pageId: PAGE_ID });
            await flushPromises();

            expect(wrapper.findComponent(PublishedItem).exists()).toBe(true);
        });

        it("does not render embed container", async () => {
            const wrapper = mountComponent({ pageId: PAGE_ID });
            await flushPromises();

            expect(wrapper.find(".page-view.embed").exists()).toBe(false);
        });
    });

    describe("embed mode", () => {
        it("renders without PublishedItem wrapper", async () => {
            const wrapper = mountComponent({ pageId: PAGE_ID, embed: true });
            await flushPromises();

            expect(wrapper.findComponent(PublishedItem).exists()).toBe(false);
            expect(wrapper.find(".page-view.embed").exists()).toBe(true);
        });

        it("does not show edit toolbar", async () => {
            const wrapper = mountComponent({ pageId: PAGE_ID, embed: true });
            await flushPromises();

            expect(wrapper.find(".page-display-toolbar").exists()).toBe(false);
        });
    });

    describe("displayOnly mode", () => {
        it("renders without PublishedItem wrapper", async () => {
            const wrapper = mountComponent({ pageId: PAGE_ID, displayOnly: true });
            await flushPromises();

            expect(wrapper.findComponent(PublishedItem).exists()).toBe(false);
            expect(wrapper.find(".page-view.embed").exists()).toBe(true);
        });

        it("shows edit toolbar with Edit Page button", async () => {
            const wrapper = mountComponent({ pageId: PAGE_ID, displayOnly: true });
            await flushPromises();

            const toolbar = wrapper.find(".page-display-toolbar");
            expect(toolbar.exists()).toBe(true);

            const editBtn = wrapper.find('[data-description="page view edit button"]');
            expect(editBtn.exists()).toBe(true);
            expect(editBtn.text()).toContain("Edit Report");
        });

        it("shows page title in toolbar", async () => {
            const wrapper = mountComponent({ pageId: PAGE_ID, displayOnly: true });
            await flushPromises();

            const toolbar = wrapper.find(".page-display-toolbar");
            expect(toolbar.text()).toContain("Test Page");
        });

        it("hides duplicate heading when displayOnly", async () => {
            const wrapper = mountComponent({ pageId: PAGE_ID, displayOnly: true, showHeading: true });
            await flushPromises();

            // The Heading component should not render because displayOnly suppresses it
            expect(wrapper.findComponent(Heading).exists()).toBe(false);
        });
    });
});
