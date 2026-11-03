import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { defineComponent } from "vue";

import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";

describe("vitest setup createStubs hook", () => {
    enableAutoUnmount(afterEach);

    it("keeps v-model on a shallow-mounted component that opted out of compat v-model", async () => {
        const Parent = defineComponent({
            components: { GFormInput },
            data: () => ({ name: "first" }),
            template: `<GFormInput v-model="name" />`,
        });
        const wrapper = shallowMount(Parent);
        const input = wrapper.getComponent(GFormInput);
        expect(input.props("modelValue")).toBe("first");

        input.vm.$emit("update:modelValue", "second");
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.name).toBe("second");
    });

    it("still stubs components that keep compat v-model", () => {
        const Child = defineComponent({ template: "<span>real</span>" });
        const Parent = defineComponent({
            components: { Child },
            template: `<Child />`,
        });
        const wrapper = shallowMount(Parent);
        expect(wrapper.html()).toContain("child-stub");
        expect(wrapper.text()).not.toContain("real");
    });
});
