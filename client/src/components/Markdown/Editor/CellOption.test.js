import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import CellOption from "./CellOption.vue";

enableAutoUnmount(afterEach);

function mountOption() {
    return mount(CellOption, {
        global: getLocalVue(),
        props: { title: "option-title", description: "option-description" },
    });
}

describe("CellOption", () => {
    it("shows the option title and description", () => {
        const wrapper = mountOption();

        expect(wrapper.get(".font-weight-bold").text()).toBe("option-title");
        expect(wrapper.get("small").text()).toBe("option-description");
    });

    it("adds an icon when the icon prop is supplied", async () => {
        const wrapper = mountOption();
        expect(wrapper.find("[data-icon='plus']").exists()).toBe(false);

        await wrapper.setProps({ icon: faPlus });

        expect(wrapper.find("[data-icon='plus']").exists()).toBe(true);
    });
});
