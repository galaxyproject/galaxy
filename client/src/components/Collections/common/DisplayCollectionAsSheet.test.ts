import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { computed, ref } from "vue";

import DisplayCollectionAsSheet from "./DisplayCollectionAsSheet.vue";

vi.mock("@/composables/datasetCollections", () => ({
    useDetailedCollection: () => ({
        collection: computed(() => null),
        collectionLoadError: computed(() => "Collection not found"),
    }),
}));

vi.mock("@/composables/useAgGrid", () => ({
    useAgGrid: () => ({
        gridApi: ref(null),
        AgGridVue: { name: "AgGridVue", render: () => null },
        onGridReady: () => {},
        theme: "ag-theme-alpine",
    }),
}));

const localVue = getLocalVue();

describe("DisplayCollectionAsSheet", () => {
    it("shows the load error instead of loading forever", () => {
        const wrapper = mount(DisplayCollectionAsSheet, {
            props: { collectionId: "collection-1" },
            global: localVue,
        });

        expect(wrapper.text()).toContain("Collection not found");
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(false);
    });
});
