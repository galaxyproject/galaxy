import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import FormCard from "./FormCard.vue";

enableAutoUnmount(afterEach);

describe("FormCard", () => {
    it("renders the title, description, and icon class", () => {
        const wrapper = shallowMount(FormCard, {
            props: {
                title: "title",
                description: "description",
                icon: "icon-class",
            },
            global: getLocalVue(),
        });
        expect(wrapper.find(".portlet-title-text").text()).toBe("title");
        expect(wrapper.find(".portlet-title-description").text()).toBe("description");
        expect(wrapper.find(".portlet-title-icon").classes()).toContain("icon-class");
    });
});
