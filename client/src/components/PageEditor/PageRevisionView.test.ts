import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { PageRevisionDetails } from "@/api/pages";

import PageRevisionView from "./PageRevisionView.vue";

const localVue = getLocalVue();

const REVISION: PageRevisionDetails = {
    id: "rev-1",
    page_id: "page-1",
    edit_source: "user",
    create_time: "2025-01-01T00:00:00Z",
    update_time: "2025-01-01T00:00:00Z",
    title: "Test Revision",
    content: "# Title\nOld line 1\nOld line 2",
    content_format: "markdown",
};

const CURRENT_CONTENT = "# Title\nNew line 1\nNew line 2\nExtra line";

function mountComponent(overrides: Record<string, unknown> = {}) {
    return shallowMount(PageRevisionView as object, {
        localVue,
        propsData: {
            revision: REVISION,
            currentContent: CURRENT_CONTENT,
            viewMode: "preview",
            isReverting: false,
            ...overrides,
        },
    });
}

describe("PageRevisionView", () => {
    describe("preview mode (default)", () => {
        it("renders Markdown component, no diff elements", () => {
            const wrapper = mountComponent();
            // Markdown is shallow-stubbed; locate via its markdownconfig prop
            const markdownStub = wrapper.find("[markdownconfig]");
            expect(markdownStub.exists()).toBe(true);
            expect(wrapper.find('[data-description="revision diff view"]').exists()).toBe(false);
        });
    });

    describe("changes mode", () => {
        it("renders diff stats and diff lines, no Markdown component", () => {
            const wrapper = mountComponent({ viewMode: "changes" });
            expect(wrapper.find("[markdownconfig]").exists()).toBe(false);
            expect(wrapper.find('[data-description="revision diff view"]').exists()).toBe(true);
            const text = wrapper.find(".diff-stats").text();
            expect(text).toContain("+3");
            expect(text).toContain("-2");
            expect(text).toContain("lines");
        });

        it("shows added lines with diff-added class", () => {
            const wrapper = mountComponent({ viewMode: "changes" });
            expect(wrapper.findAll(".diff-added").length).toBeGreaterThan(0);
        });

        it("shows removed lines with diff-removed class", () => {
            const wrapper = mountComponent({ viewMode: "changes" });
            expect(wrapper.findAll(".diff-removed").length).toBeGreaterThan(0);
        });

        it("shows 'No changes' when revision matches current content", () => {
            const wrapper = mountComponent({
                viewMode: "changes",
                currentContent: REVISION.content,
            });
            expect(wrapper.find('[data-description="revision no changes"]').exists()).toBe(true);
            expect(wrapper.find(".diff-stats").exists()).toBe(false);
            expect(wrapper.findAll(".diff-added").length).toBe(0);
            expect(wrapper.findAll(".diff-removed").length).toBe(0);
        });
    });

    describe("toggle buttons", () => {
        it("both toggle buttons are present", () => {
            const wrapper = mountComponent();
            expect(wrapper.find('[data-description="revision preview button"]').exists()).toBe(true);
            expect(wrapper.find('[data-description="revision changes button"]').exists()).toBe(true);
        });

        it("preview button is primary in preview mode", () => {
            const wrapper = mountComponent({ viewMode: "preview" });
            const previewBtn = wrapper.find('[data-description="revision preview button"]');
            const changesBtn = wrapper.find('[data-description="revision changes button"]');
            expect(previewBtn.attributes("variant")).toBe("primary");
            expect(changesBtn.attributes("variant")).toBe("outline-primary");
        });

        it("changes button is primary in changes mode", () => {
            const wrapper = mountComponent({ viewMode: "changes" });
            const previewBtn = wrapper.find('[data-description="revision preview button"]');
            const changesBtn = wrapper.find('[data-description="revision changes button"]');
            expect(previewBtn.attributes("variant")).toBe("outline-primary");
            expect(changesBtn.attributes("variant")).toBe("primary");
        });

        it("clicking Changes emits update:viewMode with 'changes'", async () => {
            const wrapper = mountComponent({ viewMode: "preview" });
            await wrapper.find('[data-description="revision changes button"]').trigger("click");
            expect(wrapper.emitted("update:viewMode")).toEqual([["changes"]]);
        });

        it("clicking Preview emits update:viewMode with 'preview'", async () => {
            const wrapper = mountComponent({ viewMode: "changes" });
            await wrapper.find('[data-description="revision preview button"]').trigger("click");
            expect(wrapper.emitted("update:viewMode")).toEqual([["preview"]]);
        });
    });

    describe("action buttons", () => {
        it("restore button is visible in preview mode", () => {
            const wrapper = mountComponent({ viewMode: "preview" });
            expect(wrapper.find('[data-description="revision restore button"]').exists()).toBe(true);
        });

        it("restore button is visible in changes mode", () => {
            const wrapper = mountComponent({ viewMode: "changes" });
            expect(wrapper.find('[data-description="revision restore button"]').exists()).toBe(true);
        });

        it("restore button is disabled when reverting", () => {
            const wrapper = mountComponent({ isReverting: true });
            expect(wrapper.find('[data-description="revision restore button"]').attributes("disabled")).toBe("true");
        });

        it("restore button emits restore with revision id", async () => {
            const wrapper = mountComponent();
            await wrapper.find('[data-description="revision restore button"]').trigger("click");
            expect(wrapper.emitted("restore")).toEqual([[REVISION.id]]);
        });

        it("back button emits back in preview mode", async () => {
            const wrapper = mountComponent({ viewMode: "preview" });
            await wrapper.find('[data-description="revision back button"]').trigger("click");
            expect(wrapper.emitted("back")).toHaveLength(1);
        });

        it("back button emits back in changes mode", async () => {
            const wrapper = mountComponent({ viewMode: "changes" });
            await wrapper.find('[data-description="revision back button"]').trigger("click");
            expect(wrapper.emitted("back")).toHaveLength(1);
        });
    });
});
