import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { CompositeSlot } from "../types/uploadItem";

import CompositeSlotRow from "./CompositeSlotRow.vue";

const BASE = { slotName: "data", description: "Data file", optional: false };

function mountRow(slotItem: CompositeSlot) {
    return mount(CompositeSlotRow, {
        props: { slotItem },
        global: { ...getLocalVue(), stubs: { RemoteFileBrowserModal: true } },
    });
}

describe("CompositeSlotRow", () => {
    it("emits the typed URL as a string", async () => {
        const wrapper = mountRow({ ...BASE, mode: "url", url: "" });
        const input = wrapper.get("[data-test-id='composite-slot-url-input']");
        expect(input.classes()).toContain("g-form-input");

        await input.setValue("https://example.org/data.txt");
        expect(wrapper.emitted("update:slotItem")).toEqual([
            [{ ...BASE, mode: "url", url: "https://example.org/data.txt" }],
        ]);
    });

    it("marks an invalid URL as invalid", () => {
        const wrapper = mountRow({ ...BASE, mode: "url", url: "not-a-url" });
        expect(wrapper.get("[data-test-id='composite-slot-url-input']").attributes("aria-invalid")).toBe("true");
    });

    it("shows the remote file name in a read-only input", () => {
        const wrapper = mountRow({
            ...BASE,
            mode: "remote",
            remoteUri: "gxftp://reads.fastq",
            remoteName: "reads.fastq",
            fileSize: 10,
        });
        const input = wrapper.get(".slot-file-name-input");
        expect(input.classes()).toContain("g-form-input");
        expect(input.attributes("readonly")).toBeDefined();
        expect((input.element as HTMLInputElement).value).toBe("reads.fastq");
    });
});
