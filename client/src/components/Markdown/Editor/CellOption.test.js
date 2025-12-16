import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import Target from "./CellOption.vue";

const localVue = getLocalVue();

function mountTarget(props = {}) {
    return mount(Target, {
        global: localVue,
        props: props,
    });
}

describe("CellOption.vue", () => {
    it("should render button", async () => {
        const wrapper = mountTarget({
            title: "option-title",
            description: "option-description",
        });
        expect(wrapper.find(".font-weight-bold").text()).toBe("option-title");
        expect(wrapper.find("small").text()).toBe("option-description");
        expect(wrapper.find("[data-icon='plus']").exists()).toBeFalsy();
        await wrapper.setProps({ icon: faPlus });
        expect(wrapper.find("[data-icon='plus']").exists()).toBeTruthy();
    });
});
