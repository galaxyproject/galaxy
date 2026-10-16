import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DatasetPermissionsForm from "./DatasetPermissionsForm.vue";

const localVue = getLocalVue();

function mountForm(checked: boolean) {
    return mount(DatasetPermissionsForm as object, {
        props: {
            loading: false,
            simplePermissions: true,
            title: "Dataset permissions",
            checked,
            formConfig: {},
        },
        global: { ...localVue, stubs: { ...localVue.stubs, FormGeneric: true } },
    });
}

describe("DatasetPermissionsForm", () => {
    it("shows the private switch with the current value", () => {
        const wrapper = mountForm(true);
        const input = wrapper.get<HTMLInputElement>("input[type='checkbox']");

        expect(input.element.checked).toBe(true);
        expect(wrapper.text()).toContain("Make new datasets private");
    });

    it("emits change with the new checked value", async () => {
        const wrapper = mountForm(false);

        await wrapper.get("input[type='checkbox']").setValue(true);

        expect(wrapper.emitted("change")).toEqual([[true]]);
    });
});
