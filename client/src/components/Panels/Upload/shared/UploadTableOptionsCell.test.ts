import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { RowOptionDescriptor } from "@/composables/upload/uploadOptionBindings";

import UploadTableOptionsCell from "./UploadTableOptionsCell.vue";

const options: RowOptionDescriptor[] = [
    { key: "spaceToTab", label: "Spaces", title: "Convert spaces to tabs", checked: false },
    { key: "deferred", label: "Defer", title: "Defer dataset resolution", checked: true },
];

describe("UploadTableOptionsCell", () => {
    it("renders one checkbox per option with the test id on the input", () => {
        const wrapper = mount(UploadTableOptionsCell as object, { props: { options } });

        const inputs = wrapper.findAll("input[type='checkbox']");
        expect(inputs).toHaveLength(2);
        expect((inputs[0]!.element as HTMLInputElement).checked).toBe(false);
        expect((inputs[1]!.element as HTMLInputElement).checked).toBe(true);
        expect(inputs[1]!.attributes("data-test-id")).toBe("deferred-toggle");
    });

    it("emits the option key with the new checked state", async () => {
        const wrapper = mount(UploadTableOptionsCell as object, { props: { options } });

        await wrapper.findAll("input[type='checkbox']")[0]!.setValue(true);
        await wrapper.find("input[data-test-id='deferred-toggle']").setValue(false);

        expect(wrapper.emitted("update")).toEqual([
            [{ key: "spaceToTab", value: true }],
            [{ key: "deferred", value: false }],
        ]);
    });
});
