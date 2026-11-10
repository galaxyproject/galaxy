import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import StorageOperationOutcomeProgress from "./StorageOperationOutcomeProgress.vue";

function mountProgress(counts: {
    totalCount: number;
    succeededCount: number;
    failedCount: number;
    skippedCount: number;
}) {
    return mount(StorageOperationOutcomeProgress, {
        props: { ...counts, showDetails: false },
    });
}

describe("StorageOperationOutcomeProgress", () => {
    it("names the track and shows one named bar per outcome against the total", () => {
        const wrapper = mountProgress({ totalCount: 10, succeededCount: 5, failedCount: 2, skippedCount: 1 });

        const track = wrapper.get('[role="group"]');
        expect(track.attributes("aria-label")).toBe("Progress: 8 / 10 (80%)");

        const bars = track.findAll('[role="progressbar"]');
        expect(bars.map((bar) => bar.attributes("aria-label"))).toEqual(["Success", "Failed", "Skipped"]);
        expect(bars.map((bar) => bar.attributes("aria-valuenow"))).toEqual(["5", "2", "1"]);
        expect(bars.map((bar) => bar.attributes("aria-valuemax"))).toEqual(["10", "10", "10"]);
    });

    it("keeps a valid range when there is nothing to process", () => {
        const wrapper = mountProgress({ totalCount: 0, succeededCount: 0, failedCount: 0, skippedCount: 0 });

        const bars = wrapper.findAll('[role="progressbar"]');
        expect(bars.map((bar) => bar.attributes("aria-valuemax"))).toEqual(["1", "1", "1"]);
        expect(bars.map((bar) => bar.attributes("aria-valuenow"))).toEqual(["0", "0", "0"]);
    });

    it("shows percentages only on the track tall enough for text", async () => {
        const wrapper = mountProgress({ totalCount: 10, succeededCount: 5, failedCount: 2, skippedCount: 1 });
        const barTexts = () => wrapper.findAll('[role="progressbar"]').map((bar) => bar.text());
        expect(barTexts()).toEqual(["", "", ""]);

        await wrapper.setProps({ heightClass: "storage-operation-progress-md" });
        expect(barTexts()).toEqual(["50%", "20%", "10%"]);
    });

    it("sets the track's height class", async () => {
        const wrapper = mountProgress({ totalCount: 1, succeededCount: 1, failedCount: 0, skippedCount: 0 });
        expect(wrapper.get('[role="group"]').classes()).toContain("storage-operation-progress-sm");

        await wrapper.setProps({ heightClass: "storage-operation-progress-md" });
        expect(wrapper.get('[role="group"]').classes()).toContain("storage-operation-progress-md");
    });
});
