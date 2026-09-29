import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import BioComputeObjectExportCard from "./BioComputeObjectExportCard.vue";

const localVue = getLocalVue(true);

describe("BioComputeObjectExportCard", () => {
    it("renders the localized submit button text", () => {
        const wrapper = shallowMount(BioComputeObjectExportCard, {
            propsData: { invocationId: "abc" },
            localVue,
            stubs: {
                GTabs: { template: "<div><slot /></div>" },
                GTab: { template: "<div><slot /></div>" },
            },
        });
        expect(wrapper.find("button.btn-primary").text()).toBe("test_localized<Submit>");
    });
});
