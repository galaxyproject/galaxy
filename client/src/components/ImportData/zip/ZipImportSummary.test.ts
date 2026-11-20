import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, h, type PropType } from "vue";

import type { ImportableFile } from "@/composables/zipExplorer";

import ZipImportSummary from "./ZipImportSummary.vue";

const SELECTORS = {
    CARD: ".summary-card-stub",
    PAGE_BUTTON: "nav[aria-label='Pagination'] button[data-page]",
    CURRENT_PAGE: "nav[aria-label='Pagination'] button[aria-current='page']",
};

const SummaryCardStub = defineComponent({
    props: { file: { type: Object as PropType<ImportableFile>, required: true } },
    setup(props) {
        return () => h("div", { class: "summary-card-stub", "data-path": props.file.path });
    },
});

function makeFiles(count: number) {
    return Array.from(
        { length: count },
        (_, index) =>
            ({ name: `file-${index + 1}`, path: `file-${index + 1}`, size: 1, type: "file" }) as ImportableFile,
    );
}

function mountSummary(fileCount: number) {
    const localVue = getLocalVue();
    return mount(ZipImportSummary as object, {
        props: { filesToImport: makeFiles(fileCount) },
        global: { ...localVue, stubs: { ...localVue.stubs, ZipFileEntrySummaryCard: SummaryCardStub } },
    });
}

describe("ZipImportSummary", () => {
    it("pages through the files to import", async () => {
        const wrapper = mountSummary(30);

        expect(wrapper.findAll(SELECTORS.CARD)).toHaveLength(24);
        expect(wrapper.find(SELECTORS.CURRENT_PAGE).text()).toBe("1");

        await wrapper.find(`${SELECTORS.PAGE_BUTTON}[data-page='2']`).trigger("click");

        expect(wrapper.find(SELECTORS.CURRENT_PAGE).text()).toBe("2");
        expect(wrapper.findAll(SELECTORS.CARD).map((card) => card.attributes("data-path"))).toEqual(
            makeFiles(30)
                .slice(24)
                .map((file) => file.path),
        );
    });

    it("shows no pager when every file fits on one page", () => {
        const wrapper = mountSummary(24);

        expect(wrapper.find("nav[aria-label='Pagination']").exists()).toBe(false);
    });
});
