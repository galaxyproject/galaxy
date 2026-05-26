import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import SplitView from "./SplitView.vue";
import DraggableSeparator from "@/components/Common/DraggableSeparator.vue";

const localVue = getLocalVue();

function mountComponent(propsData = {}) {
    return shallowMount(SplitView as object, {
        localVue,
        propsData,
        slots: {
            left: '<div class="test-left">Left</div>',
            right: '<div class="test-right">Right</div>',
        },
    });
}

describe("SplitView", () => {
    it("renders split view container", () => {
        const wrapper = mountComponent();
        expect(wrapper.find('[data-description="split view"]').exists()).toBe(true);
    });

    it("renders left slot", () => {
        const wrapper = mountComponent();
        expect(wrapper.find(".test-left").exists()).toBe(true);
    });

    it("renders right slot", () => {
        const wrapper = mountComponent();
        expect(wrapper.find(".test-right").exists()).toBe(true);
    });

    it("delegates the divider to DraggableSeparator", () => {
        const wrapper = mountComponent();
        expect(wrapper.findComponent(DraggableSeparator).exists()).toBe(true);
    });
});
