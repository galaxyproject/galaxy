import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import FormRepeat from "./FormRepeat.vue";

const localVue = getLocalVue();

describe("FormRepeat", () => {
    it("titles repeat blocks from 1", () => {
        const wrapper = mount(FormRepeat as object, {
            props: {
                input: { name: "queries", title: "Dataset", min: 0, default: 0, max: "", cache: [[], []] },
                passthroughProps: { onChange: () => {}, onChangeForm: () => {} },
            },
            global: { ...localVue, stubs: { FormNode: true, FormListElementOperations: true } },
        });
        const titles = wrapper.findAll("[data-description='repeat block'] .portlet-title-text").map((t) => t.text());
        expect(titles).toEqual(["1: Dataset", "2: Dataset"]);
    });
});
