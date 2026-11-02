import { nth } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import FormColumnDefinition from "./FormColumnDefinition.vue";

describe("FormColumnDefinition", () => {
    it("marks the column optional when the checkbox is checked", async () => {
        const wrapper = mount(FormColumnDefinition as object, {
            props: {
                value: { name: "condition", type: "string", description: "", optional: false },
                index: 2,
                prefix: "column_2",
            },
            global: { stubs: { FormElement: true, FormColumnDefinitionType: true } },
        });

        await wrapper.find("#column_2_optional").setValue(true);

        const [state, index] = nth(wrapper.emitted<[Record<string, unknown>, number]>("onChange"), -1);
        expect(state.optional).toBe(true);
        expect(index).toBe(2);
    });
});
