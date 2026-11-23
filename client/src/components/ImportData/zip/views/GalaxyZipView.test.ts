import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { defineComponent, h, type PropType } from "vue";

import type { ImportableFile } from "@/composables/zipExplorer";

import GalaxyZipView from "./GalaxyZipView.vue";

const FILES = Array.from(
    { length: 30 },
    (_, index) => ({ name: `file-${index + 1}`, path: `file-${index + 1}`, size: 1, type: "file" }) as ImportableFile,
);

vi.mock("@/composables/zipExplorer", async (importOriginal) => ({
    ...(await importOriginal<Record<string, unknown>>()),
    getImportableFiles: () => FILES,
}));

const SELECTORS = {
    CARD: ".entry-card-stub",
    PAGE_BUTTON: "nav[aria-label='Pagination'] button[data-page]",
    CURRENT_PAGE: "nav[aria-label='Pagination'] button[aria-current='page']",
};

const EntryCardStub = defineComponent({
    props: { file: { type: Object as PropType<ImportableFile>, required: true } },
    setup(props) {
        return () => h("div", { class: "entry-card-stub", "data-path": props.file.path });
    },
});

describe("GalaxyZipView", () => {
    it("pages through the files in the export archive", async () => {
        const localVue = getLocalVue();
        const wrapper = mount(GalaxyZipView as object, {
            props: { explorer: {} },
            global: { ...localVue, stubs: { ...localVue.stubs, ZipFileEntryCard: EntryCardStub } },
        });

        expect(wrapper.findAll(SELECTORS.CARD)).toHaveLength(24);

        await wrapper.find(`${SELECTORS.PAGE_BUTTON}[data-page='2']`).trigger("click");

        expect(wrapper.find(SELECTORS.CURRENT_PAGE).text()).toBe("2");
        expect(wrapper.findAll(SELECTORS.CARD).map((card) => card.attributes("data-path"))).toEqual(
            FILES.slice(24).map((file) => file.path),
        );
    });
});
