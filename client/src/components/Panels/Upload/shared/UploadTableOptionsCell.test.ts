import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { RowOptionDescriptor } from "@/composables/upload/uploadOptionBindings";

import UploadTableOptionsCell from "./UploadTableOptionsCell.vue";

const options: RowOptionDescriptor[] = [
    { key: "spaceToTab", label: "Spaces", title: "Convert spaces to tabs", checked: false },
    { key: "deferred", label: "Defer", title: "Defer dataset resolution", checked: true },
];

describe("UploadTableOptionsCell", () => {
    it("emits the option key with the new checked state", async () => {
        const wrapper = mount(UploadTableOptionsCell, { props: { options } });
        const deferred = wrapper.find("input[data-test-id='deferred-toggle']");
        expect((deferred.element as HTMLInputElement).checked).toBe(true);

        await wrapper.findAll("input[type='checkbox']")[0]!.setValue(true);
        await deferred.setValue(false);

        expect(wrapper.emitted("update")).toEqual([
            [{ key: "spaceToTab", value: true }],
            [{ key: "deferred", value: false }],
        ]);
    });
});
