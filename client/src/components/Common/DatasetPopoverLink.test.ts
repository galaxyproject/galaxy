import { createTestingPinia } from "@pinia/testing";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { HDADetailed } from "@/api";

import DatasetPopoverLink from "./DatasetPopoverLink.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";

enableAutoUnmount(afterEach);

// The stubbed details child only needs the cached dataset identity and name.
type CachedDatasetName = Pick<HDADetailed, "id" | "name">;

function mountPopover(storedDatasets: Record<string, CachedDatasetName> = {}) {
    const wrapper = shallowMount(DatasetPopoverLink, {
        props: { datasetId: "dataset_id" },
        global: {
            plugins: [createTestingPinia({ createSpy: vi.fn, initialState: { datasetStore: { storedDatasets } } })],
            stubs: { RouterLink: true },
        },
    });
    return wrapper.getComponent(GPopover);
}

describe("DatasetPopoverLink", () => {
    it("lets keyboard users reach the links in the dataset details", () => {
        expect(mountPopover().props("interactive")).toBe(true);
    });

    it("uses a generic details label until the dataset is cached", () => {
        expect(mountPopover().props("ariaLabel")).toBe("Dataset details");
    });

    it("names the details dialog with the cached dataset name", () => {
        const popover = mountPopover({ dataset_id: { id: "dataset_id", name: "reads.fastq" } });
        expect(popover.props("ariaLabel")).toBe("reads.fastq");
    });
});
