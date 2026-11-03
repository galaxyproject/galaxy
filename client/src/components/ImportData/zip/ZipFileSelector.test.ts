import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, h, type PropType } from "vue";

import type { ImportableFile } from "@/composables/zipExplorer";

import ZipFileSelector from "./ZipFileSelector.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";

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

function makeFiles(prefix: string, count: number) {
    return Array.from(
        { length: count },
        (_, index) =>
            ({
                name: `${prefix}-${index + 1}`,
                path: `${prefix}-${index + 1}`,
                size: 1,
                type: "file",
            }) as ImportableFile,
    );
}

const ALPHA_FILES = makeFiles("alpha", 30);
const BETA_FILES = makeFiles("beta", 30);

function mountSelector() {
    const localVue = getLocalVue();
    return mount(ZipFileSelector as object, {
        props: {
            zipSource: "https://example.org/archive.zip",
            zipContents: { workflows: [], files: [...ALPHA_FILES, ...BETA_FILES] },
            selectedItems: [],
        },
        global: {
            ...localVue,
            stubs: { ...localVue.stubs, ListHeader: true, ZipFileEntryCard: EntryCardStub },
        },
    });
}

function shownPaths(wrapper: ReturnType<typeof mountSelector>) {
    return wrapper.findAll(SELECTORS.CARD).map((card) => card.attributes("data-path"));
}

describe("ZipFileSelector", () => {
    it("pages through the files in the archive", async () => {
        const wrapper = mountSelector();

        expect(wrapper.findAll(SELECTORS.PAGE_BUTTON).map((button) => button.text())).toEqual(["1", "2", "3"]);
        expect(shownPaths(wrapper)).toEqual(ALPHA_FILES.slice(0, 24).map((file) => file.path));

        await wrapper.find(`${SELECTORS.PAGE_BUTTON}[data-page='3']`).trigger("click");

        expect(wrapper.find(SELECTORS.CURRENT_PAGE).text()).toBe("3");
        expect(shownPaths(wrapper)).toEqual(BETA_FILES.slice(18).map((file) => file.path));
    });

    it("goes back to the first page when the search changes", async () => {
        const wrapper = mountSelector();
        await wrapper.find(`${SELECTORS.PAGE_BUTTON}[data-page='3']`).trigger("click");

        wrapper.findComponent(DelayedInput).vm.$emit("change", "beta");
        await wrapper.vm.$nextTick();

        expect(wrapper.findAll(SELECTORS.PAGE_BUTTON).map((button) => button.text())).toEqual(["1", "2"]);
        expect(wrapper.find(SELECTORS.CURRENT_PAGE).text()).toBe("1");
        expect(shownPaths(wrapper)).toEqual(BETA_FILES.slice(0, 24).map((file) => file.path));
    });
});
