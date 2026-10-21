import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { defineComponent, ref } from "vue";

import GCollapse from "./GCollapse.vue";
import GTab from "./GTab.vue";
import GTabs from "./GTabs.vue";

enableAutoUnmount(afterEach);

// v-model has to mean modelValue/update:modelValue in both consumers. Compat would also map it onto Vue 2's
// value/input, so these guard the client side (the compat opt-out, the modelValue prop); the Tool Shed's
// galaxyUi.test.ts covers plain Vue 3, where value/input silently does nothing.
describe("galaxy-ui v-model", () => {
    it("binds the active tab both ways on GTabs", async () => {
        const Parent = defineComponent({
            components: { GTabs, GTab },
            setup: () => ({ active: ref(1) }),
            template: `<GTabs v-model="active"><GTab title="One">one</GTab><GTab title="Two">two</GTab></GTabs>`,
        });
        const wrapper = mount(Parent);
        await flushPromises();

        expect(wrapper.get(".nav-link.active").text()).toBe("Two");

        await wrapper.get(".nav-link").trigger("click");

        expect(wrapper.vm.active).toBe(0);
    });

    it("opens and closes GCollapse from its v-model", async () => {
        const Parent = defineComponent({
            components: { GCollapse },
            setup: () => ({ open: ref(false) }),
            template: `<GCollapse v-model="open">details</GCollapse>`,
        });
        const wrapper = mount(Parent);
        await flushPromises();
        expect(wrapper.classes()).not.toContain("g-collapse-open");

        wrapper.vm.open = true;
        await flushPromises();

        expect(wrapper.classes()).toContain("g-collapse-open");
    });
});
