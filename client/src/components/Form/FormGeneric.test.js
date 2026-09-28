import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import FormGeneric from "./FormGeneric.vue";

vi.mock("@/components/providers/UrlDataProvider", () => ({
    UrlDataProvider: {
        render() {
            return this.$scopedSlots.default({
                loading: false,
                result: { inputs: [], title: "", icon: null },
            });
        },
    },
}));

const localVue = getLocalVue(true);

describe("FormGeneric", () => {
    it("renders localized submit and cancel button text", () => {
        const wrapper = mount(FormGeneric, {
            propsData: {
                url: "/api/whatever",
                cancelRedirect: "/somewhere",
            },
            localVue,
        });
        expect(wrapper.text()).toContain("test_localized<Save>");
        expect(wrapper.text()).toContain("test_localized<Cancel>");
    });
});
