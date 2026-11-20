import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { computed, defineComponent, h, ref } from "vue";

import UploadProgress from "./UploadProgress.vue";

const UPLOADS = Array.from({ length: 30 }, (_, index) => ({ id: `upload-${index + 1}` }));

vi.mock("./uploadState", () => ({
    useUploadState: () => {
        const items = ref(UPLOADS);
        return {
            activeItems: items,
            activeBatches: ref([]),
            batchesWithProgress: computed(() => []),
            hasActiveUploads: computed(() => false),
            hasCompleted: computed(() => false),
            orderedUploadItems: computed(() => items.value.map((upload) => ({ type: "upload", upload }))),
        };
    },
}));

vi.mock("@/composables/upload/useUploadBatchOperations", () => ({
    useUploadBatchOperations: () => ({}),
}));

vi.mock("@/stores/uploadDatasetMonitorStore", () => ({
    useUploadDatasetMonitorStore: () => ({}),
}));

const SELECTORS = {
    ROW: ".upload-row-stub",
    PAGE_BUTTON: "nav[aria-label='Pagination'] button[data-page]",
    CURRENT_PAGE: "nav[aria-label='Pagination'] button[aria-current='page']",
};

const UploadFileRowStub = defineComponent({
    props: { file: { type: Object, required: true } },
    setup(props) {
        return () => h("div", { class: "upload-row-stub", "data-id": props.file.id });
    },
});

describe("UploadProgress", () => {
    it("pages through the uploads", async () => {
        const localVue = getLocalVue();
        const wrapper = mount(UploadProgress as object, {
            global: {
                ...localVue,
                stubs: { ...localVue.stubs, BreadcrumbHeading: true, UploadFileRow: UploadFileRowStub },
            },
        });

        expect(wrapper.findAll(SELECTORS.ROW)).toHaveLength(24);
        expect(wrapper.find(SELECTORS.CURRENT_PAGE).text()).toBe("1");

        await wrapper.find(`${SELECTORS.PAGE_BUTTON}[data-page='2']`).trigger("click");

        expect(wrapper.find(SELECTORS.CURRENT_PAGE).text()).toBe("2");
        expect(wrapper.findAll(SELECTORS.ROW).map((row) => row.attributes("data-id"))).toEqual(
            UPLOADS.slice(24).map((upload) => upload.id),
        );
    });
});
