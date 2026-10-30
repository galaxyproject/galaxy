import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, h, ref } from "vue";

import GPagination from "./GPagination.vue";

type Props = InstanceType<typeof GPagination>["$props"];
type Wrapper = { findAll: ReturnType<typeof mount>["findAll"]; get: ReturnType<typeof mount>["get"] };

function mountPagination(props: Props = {}, attachTo?: HTMLElement) {
    return mount(GPagination, { props: { totalRows: 100, perPage: 10, ...props }, attachTo });
}

// What the user sees, in order: page numbers, end-button glyphs and ellipses
function visibleItems(wrapper: Wrapper) {
    return wrapper.findAll("li").map((item) => item.text());
}

function pageButton(wrapper: Wrapper, page: number) {
    return wrapper.get(`button[aria-label="Go to page ${page}"]`);
}

function mountWithModel(initial: number, total = ref(100), perPage = ref(10)) {
    const page = ref(initial);
    const Parent = defineComponent({
        setup() {
            return () =>
                h(GPagination, {
                    modelValue: page.value,
                    "onUpdate:modelValue": (value: number) => (page.value = value),
                    totalRows: total.value,
                    perPage: perPage.value,
                });
        },
    });
    return { page, total, perPage, wrapper: mount(Parent) };
}

describe("GPagination", () => {
    it("is a navigation landmark with a default and a custom label", () => {
        expect(mountPagination().get("nav").attributes("aria-label")).toBe("Pagination");
        expect(mountPagination({ ariaLabel: "Dataset pages" }).get("nav").attributes("aria-label")).toBe(
            "Dataset pages",
        );
    });

    it("shows a window of pages with end buttons and an ellipsis", () => {
        expect(visibleItems(mountPagination({ modelValue: 1 }))).toEqual(["«", "‹", "1", "2", "3", "4", "…", "›", "»"]);
        expect(visibleItems(mountPagination({ modelValue: 5 }))).toEqual(["«", "‹", "…", "4", "5", "6", "…", "›", "»"]);
        expect(visibleItems(mountPagination({ modelValue: 10 }))).toEqual([
            "«",
            "‹",
            "…",
            "7",
            "8",
            "9",
            "10",
            "›",
            "»",
        ]);
    });

    it("pins the first and last page numbers in place of the end buttons", () => {
        const props = { firstNumber: true, lastNumber: true };

        expect(visibleItems(mountPagination({ ...props, modelValue: 1 }))).toEqual([
            "‹",
            "1",
            "2",
            "3",
            "4",
            "5",
            "…",
            "10",
            "›",
        ]);
        expect(visibleItems(mountPagination({ ...props, modelValue: 5 }))).toEqual([
            "‹",
            "1",
            "…",
            "4",
            "5",
            "6",
            "…",
            "10",
            "›",
        ]);
        expect(visibleItems(mountPagination({ ...props, modelValue: 10 }))).toEqual([
            "‹",
            "1",
            "…",
            "6",
            "7",
            "8",
            "9",
            "10",
            "›",
        ]);
    });

    it("shows no ellipses with a limit of 3 or less", () => {
        expect(visibleItems(mountPagination({ limit: 3, modelValue: 1 }))).toEqual(["«", "‹", "1", "2", "3", "›", "»"]);
        expect(visibleItems(mountPagination({ limit: 3, modelValue: 5 }))).toEqual(["«", "‹", "4", "5", "6", "›", "»"]);
        expect(visibleItems(mountPagination({ limit: 3, modelValue: 10 }))).toEqual([
            "«",
            "‹",
            "8",
            "9",
            "10",
            "›",
            "»",
        ]);
        expect(visibleItems(mountPagination({ limit: 1, modelValue: 5 }))).toEqual(["«", "‹", "5", "›", "»"]);
    });

    it("keeps a compact pager to the current page between the pinned ends", () => {
        const props = { limit: 3, firstNumber: true, lastNumber: true, hideGotoEndButtons: true };

        expect(visibleItems(mountPagination({ ...props, modelValue: 1 }))).toEqual([
            "‹",
            "1",
            "2",
            "3",
            "4",
            "10",
            "›",
        ]);
        expect(visibleItems(mountPagination({ ...props, modelValue: 5 }))).toEqual([
            "‹",
            "1",
            "4",
            "5",
            "6",
            "10",
            "›",
        ]);
        expect(visibleItems(mountPagination({ ...props, modelValue: 10 }))).toEqual([
            "‹",
            "1",
            "7",
            "8",
            "9",
            "10",
            "›",
        ]);
    });

    it("hides the first and last buttons with hideGotoEndButtons", () => {
        expect(visibleItems(mountPagination({ modelValue: 1, hideGotoEndButtons: true }))).toEqual([
            "‹",
            "1",
            "2",
            "3",
            "4",
            "…",
            "›",
        ]);
    });

    it("lists every page when they fit within the limit", () => {
        expect(visibleItems(mountPagination({ totalRows: 30, modelValue: 2 }))).toEqual([
            "«",
            "‹",
            "1",
            "2",
            "3",
            "›",
            "»",
        ]);
    });

    it("shows a single current page when there are no rows", () => {
        const wrapper = mountPagination({ totalRows: 0 });

        expect(visibleItems(wrapper)).toEqual(["«", "‹", "1", "›", "»"]);
        expect(pageButton(wrapper, 1).attributes("aria-current")).toBe("page");
        expect(wrapper.get('button[aria-label="Go to next page"]').attributes("disabled")).toBeDefined();
    });

    it("lets custom glyphs and labels replace the defaults", () => {
        const wrapper = mountPagination({
            modelValue: 1,
            totalRows: 20,
            firstText: "First",
            prevText: "Prev",
            nextText: "Next",
            lastText: "Last",
            labelNextPage: "Next page",
            labelPage: (page: number) => `Page ${page}`,
        });

        expect(visibleItems(wrapper)).toEqual(["First", "Prev", "1", "2", "Next", "Last"]);
        expect(wrapper.find('button[aria-label="Next page"]').exists()).toBe(true);
        expect(wrapper.find('button[aria-label="Page 2"]').exists()).toBe(true);
    });

    it("marks only the current page with aria-current", () => {
        const wrapper = mountPagination({ modelValue: 3 });

        expect(wrapper.findAll('[aria-current="page"]').map((button) => button.text())).toEqual(["3"]);
        expect(pageButton(wrapper, 3).attributes("data-page")).toBe("3");
    });

    it("emits the clicked page as update:modelValue and change", async () => {
        const wrapper = mountPagination({ modelValue: 1 });

        await pageButton(wrapper, 3).trigger("click");

        expect(wrapper.emitted("update:modelValue")).toEqual([[3]]);
        expect(wrapper.emitted("change")).toEqual([[3]]);
    });

    it("emits nothing when the current page is clicked", async () => {
        const wrapper = mountPagination({ modelValue: 2 });

        await pageButton(wrapper, 2).trigger("click");

        expect(wrapper.emitted("update:modelValue")).toBeUndefined();
        expect(wrapper.emitted("change")).toBeUndefined();
    });

    it("steps with the previous, next, first and last buttons", async () => {
        const wrapper = mountPagination({ modelValue: 4 });

        await wrapper.get('button[aria-label="Go to previous page"]').trigger("click");
        await wrapper.get('button[aria-label="Go to next page"]').trigger("click");
        await wrapper.get('button[aria-label="Go to first page"]').trigger("click");
        await wrapper.get('button[aria-label="Go to last page"]').trigger("click");

        expect(wrapper.emitted("change")).toEqual([[3], [5], [1], [10]]);
    });

    it("disables the backward buttons on the first page and the forward ones on the last", async () => {
        const wrapper = mountPagination({ modelValue: 1 });
        const disabled = () =>
            wrapper
                .findAll("button")
                .filter((button) => button.attributes("disabled") !== undefined)
                .map((button) => button.attributes("aria-label"));

        expect(disabled()).toEqual(["Go to first page", "Go to previous page"]);

        await wrapper.setProps({ modelValue: 10 });

        expect(disabled()).toEqual(["Go to next page", "Go to last page"]);
    });

    it("keeps ellipses out of the tab order and the accessibility tree", () => {
        const wrapper = mountPagination({ modelValue: 5 });
        const ellipses = wrapper.findAll("li").filter((item) => item.text() === "…");

        expect(ellipses).toHaveLength(2);
        for (const ellipsis of ellipses) {
            expect(ellipsis.attributes("aria-hidden")).toBe("true");
            expect(ellipsis.find("button, a, [tabindex]").exists()).toBe(false);
        }
    });

    it("disables every button when disabled", () => {
        const wrapper = mountPagination({ modelValue: 5, disabled: true });

        expect(wrapper.findAll("button").every((button) => button.attributes("disabled") !== undefined)).toBe(true);
    });

    it("points every button at the controlled region", () => {
        const wrapper = mountPagination({ modelValue: 5, ariaControls: "results-table" });

        expect(
            wrapper.findAll("button").every((button) => button.attributes("aria-controls") === "results-table"),
        ).toBe(true);
    });

    it("puts the item class props on their list items", () => {
        const wrapper = mountPagination({
            modelValue: 5,
            pageClass: "pager-page",
            prevClass: "pager-prev",
            nextClass: "pager-next",
            firstClass: "pager-first",
            lastClass: "pager-last",
            ellipsisClass: "pager-gap",
        });

        expect(wrapper.findAll("li.pager-page").map((item) => item.text())).toEqual(["4", "5", "6"]);
        expect(wrapper.get("li.pager-prev button").attributes("aria-label")).toBe("Go to previous page");
        expect(wrapper.get("li.pager-next button").attributes("aria-label")).toBe("Go to next page");
        expect(wrapper.get("li.pager-first button").attributes("aria-label")).toBe("Go to first page");
        expect(wrapper.get("li.pager-last button").attributes("aria-label")).toBe("Go to last page");
        expect(wrapper.findAll("li.pager-gap")).toHaveLength(2);
    });

    it("passes attributes such as class and data-description to the nav", () => {
        const wrapper = mount(GPagination as object, {
            props: { totalRows: 10 },
            attrs: { class: "m-0", "data-description": "grid pager" },
        });

        expect(wrapper.get("nav").classes()).toContain("m-0");
        expect(wrapper.get("nav").attributes("data-description")).toBe("grid pager");
    });

    it("keeps its own page when no modelValue is bound", async () => {
        const wrapper = mountPagination();

        expect(pageButton(wrapper, 1).attributes("aria-current")).toBe("page");

        await pageButton(wrapper, 2).trigger("click");

        expect(pageButton(wrapper, 2).attributes("aria-current")).toBe("page");
        expect(wrapper.emitted("change")).toEqual([[2]]);
    });

    it("shows a page past the end as the last page", () => {
        const wrapper = mountPagination({ modelValue: 42 });

        expect(pageButton(wrapper, 10).attributes("aria-current")).toBe("page");
    });

    it("updates the bound page both ways through v-model", async () => {
        const { page, wrapper } = mountWithModel(2);

        await pageButton(wrapper, 4).trigger("click");
        expect(page.value).toBe(4);
        expect(pageButton(wrapper, 4).attributes("aria-current")).toBe("page");

        page.value = 7;
        await flushPromises();
        expect(pageButton(wrapper, 7).attributes("aria-current")).toBe("page");
    });

    it("goes back to page 1 when the pages shrink below the current page", async () => {
        const { page, total, wrapper } = mountWithModel(8);

        total.value = 30;
        await flushPromises();

        expect(page.value).toBe(1);
        expect(wrapper.findComponent(GPagination).emitted("change")).toBeUndefined();
    });

    it("keeps the current page when the pages grow", async () => {
        const { page, total } = mountWithModel(8);

        total.value = 200;
        await flushPromises();

        expect(page.value).toBe(8);
    });

    it("goes back to page 1 when the page size changes", async () => {
        const { page, perPage } = mountWithModel(3);

        perPage.value = 25;
        await flushPromises();

        expect(page.value).toBe(1);
    });

    it("moves focus to the current page when the clicked button becomes disabled", async () => {
        const wrapper = mountPagination({ modelValue: 9 }, document.body);
        const next = wrapper.get('button[aria-label="Go to next page"]');
        (next.element as HTMLButtonElement).focus();

        await next.trigger("click");
        await wrapper.setProps({ modelValue: 10 });
        await flushPromises();

        expect(document.activeElement).toBe(pageButton(wrapper, 10).element);
        wrapper.unmount();
    });
});
