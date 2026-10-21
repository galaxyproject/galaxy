import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";

import type { PageRevisionDetails } from "@/api/pages";
import type GButton from "@/components/BaseComponents/GButton.vue";

import PageRevisionView from "./PageRevisionView.vue";

const localVue = getLocalVue();
enableAutoUnmount(afterEach);

type RevisionViewProps = InstanceType<typeof PageRevisionView>["$props"];

const REVISION = {
    id: "rev-1",
    page_id: "page-1",
    edit_source: "user",
    create_time: "2025-01-01T00:00:00Z",
    update_time: "2025-01-01T00:00:00Z",
    title: "Test Revision",
    content: "# Title\nOld line 1\nOld line 2",
    content_editor: "# Title\nOld line 1\nOld line 2",
    content_format: "markdown",
} satisfies PageRevisionDetails;

const CURRENT_CONTENT = "# Title\nNew line 1\nNew line 2\nExtra line";
const PREVIOUS_CONTENT = "# Title\nPrevious line 1";

function mountRevisionView(overrides: Partial<RevisionViewProps> = {}) {
    return shallowMount(PageRevisionView, {
        global: localVue,
        props: {
            revision: REVISION,
            currentContent: CURRENT_CONTENT,
            previousContent: PREVIOUS_CONTENT,
            isNewestRevision: false,
            isOldestRevision: false,
            viewMode: "preview",
            isReverting: false,
            ...overrides,
        },
    });
}

describe("PageRevisionView", () => {
    describe("preview mode (default)", () => {
        it("renders Markdown component, no diff elements", () => {
            const wrapper = mountRevisionView();
            // Markdown is shallow-stubbed; locate via its markdownconfig prop
            const markdownStub = wrapper.find("[markdownconfig]");
            expect(markdownStub.exists()).toBe(true);
            expect(wrapper.find('[data-description="revision diff view"]').exists()).toBe(false);
        });
    });

    describe("changes_current mode", () => {
        it("renders diff stats and diff lines, no Markdown component", () => {
            const wrapper = mountRevisionView({ viewMode: "changes_current" });
            expect(wrapper.find("[markdownconfig]").exists()).toBe(false);
            expect(wrapper.find('[data-description="revision diff view"]').exists()).toBe(true);
            const text = wrapper.get(".diff-stats").text();
            expect(text).toContain("+3");
            expect(text).toContain("-2");
            expect(text).toContain("lines");
        });

        it("shows added lines with diff-added class", () => {
            const wrapper = mountRevisionView({ viewMode: "changes_current" });
            expect(wrapper.findAll(".diff-added").length).toBeGreaterThan(0);
        });

        it("shows removed lines with diff-removed class", () => {
            const wrapper = mountRevisionView({ viewMode: "changes_current" });
            expect(wrapper.findAll(".diff-removed").length).toBeGreaterThan(0);
        });

        it("shows 'No changes' when revision matches current content", () => {
            const wrapper = mountRevisionView({
                viewMode: "changes_current",
                currentContent: REVISION.content,
            });
            expect(wrapper.find('[data-description="revision no changes"]').exists()).toBe(true);
            expect(wrapper.find(".diff-stats").exists()).toBe(false);
            expect(wrapper.findAll(".diff-added").length).toBe(0);
            expect(wrapper.findAll(".diff-removed").length).toBe(0);
        });
    });

    describe("changes_previous mode", () => {
        it("renders diff vs previous content", () => {
            const wrapper = mountRevisionView({ viewMode: "changes_previous" });
            expect(wrapper.find('[data-description="revision diff view"]').exists()).toBe(true);
            expect(wrapper.find(".diff-stats").exists()).toBe(true);
            expect(wrapper.findAll(".diff-added").length).toBeGreaterThan(0);
            expect(wrapper.findAll(".diff-removed").length).toBeGreaterThan(0);
        });

        it("shows 'No changes' when revision matches previous content", () => {
            const wrapper = mountRevisionView({
                viewMode: "changes_previous",
                previousContent: REVISION.content,
            });
            expect(wrapper.find('[data-description="revision no changes"]').exists()).toBe(true);
            expect(wrapper.find(".diff-stats").exists()).toBe(false);
        });
    });

    describe("toggle buttons", () => {
        it("preview button is always visible", () => {
            const wrapper = mountRevisionView();
            expect(wrapper.find('[data-description="revision preview button"]').exists()).toBe(true);
        });

        it("both compare buttons visible when not newest/oldest", () => {
            const wrapper = mountRevisionView();
            expect(wrapper.find('[data-description="revision compare current button"]').exists()).toBe(true);
            expect(wrapper.find('[data-description="revision compare previous button"]').exists()).toBe(true);
        });

        it("'Compare to Current' hidden when isNewestRevision", () => {
            const wrapper = mountRevisionView({ isNewestRevision: true });
            expect(wrapper.find('[data-description="revision compare current button"]').exists()).toBe(false);
            expect(wrapper.find('[data-description="revision compare previous button"]').exists()).toBe(true);
        });

        it("'Compare to Previous' hidden when isOldestRevision", () => {
            const wrapper = mountRevisionView({ isOldestRevision: true });
            expect(wrapper.find('[data-description="revision compare current button"]').exists()).toBe(true);
            expect(wrapper.find('[data-description="revision compare previous button"]').exists()).toBe(false);
        });

        it.each([
            ["preview", "revision preview button"],
            ["changes_current", "revision compare current button"],
            ["changes_previous", "revision compare previous button"],
        ] as const)("presses the selected toggle in %s mode", (viewMode, description) => {
            const wrapper = mountRevisionView({ viewMode });
            const button = wrapper.getComponent<typeof GButton>(`[data-description="${description}"]`);
            expect(button.props("pressed")).toBe(true);
        });

        it.each([
            ["changes_current", "preview", "revision compare current button"],
            ["changes_previous", "preview", "revision compare previous button"],
            ["preview", "changes_current", "revision preview button"],
        ] as const)("emits %s when its toggle is clicked from %s", async (nextMode, viewMode, description) => {
            const wrapper = mountRevisionView({ viewMode });
            wrapper.getComponent<typeof GButton>(`[data-description="${description}"]`).vm.$emit("click");
            await nextTick();
            expect(wrapper.emitted("update:viewMode")).toEqual([[nextMode]]);
        });
    });

    describe("action buttons", () => {
        it.each(["preview", "changes_current"] as const)("shows Restore in %s mode", (viewMode) => {
            const wrapper = mountRevisionView({ viewMode });
            expect(wrapper.find('[data-description="revision restore button"]').exists()).toBe(true);
        });

        it("restore button is disabled when reverting", () => {
            const wrapper = mountRevisionView({ isReverting: true });
            expect(wrapper.get('[data-description="revision restore button"]').attributes("disabled")).toBe("true");
        });

        it("restore button emits restore with revision id", async () => {
            const wrapper = mountRevisionView();
            wrapper.getComponent<typeof GButton>('[data-description="revision restore button"]').vm.$emit("click");
            await nextTick();
            expect(wrapper.emitted("restore")).toEqual([[REVISION.id]]);
        });

        it.each(["preview", "changes_current"] as const)("emits back from %s mode", async (viewMode) => {
            const wrapper = mountRevisionView({ viewMode });
            wrapper.getComponent<typeof GButton>('[data-description="revision back button"]').vm.$emit("click");
            await nextTick();
            expect(wrapper.emitted("back")).toHaveLength(1);
        });
    });
});
