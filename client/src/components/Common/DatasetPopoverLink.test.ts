import { createTestingPinia } from "@pinia/testing";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import DatasetPopoverLink from "./DatasetPopoverLink.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";

function mountLink(storedDatasets = {}) {
    const wrapper = shallowMount(DatasetPopoverLink as object, {
        props: { datasetId: "dataset_id" },
        global: {
            plugins: [createTestingPinia({ createSpy: vi.fn, initialState: { datasetStore: { storedDatasets } } })],
            stubs: { RouterLink: true },
        },
    });
    return wrapper.findComponent(GPopover);
}

describe("DatasetPopoverLink", () => {
    it("lets keyboard users reach the links in the dataset details", () => {
        expect(mountLink().props("interactive")).toBe(true);
    });

    it("names the details dialog by the dataset rather than its encoded id", () => {
        expect(mountLink().props("ariaLabel")).toBe("Dataset details");
        expect(mountLink({ dataset_id: { id: "dataset_id", name: "reads.fastq" } }).props("ariaLabel")).toBe(
            "reads.fastq",
        );
    });
});
