import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { defineComponent, h, ref } from "vue";

import FormTags from "./FormTags.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

vi.mock("@/stores/userTagsStore", () => ({
    useUserTagsStore: vi.fn(() => ({
        userTags: [],
        onNewTagSeen: vi.fn(),
        onTagUsed: vi.fn(),
        onMultipleNewTagsSeen: vi.fn(),
    })),
}));

const localVue = getLocalVue();

describe("FormTags", () => {
    it("splits the comma-separated model into tags and joins edits back", async () => {
        const model = ref("alpha, beta");
        // A modelValue/onUpdate:modelValue vnode is what a parent's v-model compiles to.
        const Parent = defineComponent({
            compatConfig: { MODE: 3 },
            setup() {
                return () =>
                    h(FormTags, {
                        modelValue: model.value,
                        "onUpdate:modelValue": (value: string) => (model.value = value),
                    });
            },
        });
        const wrapper = mount(Parent, { global: localVue });
        const tags = wrapper.findComponent(StatelessTags);

        expect(tags.props("modelValue")).toEqual(["alpha", "beta"]);

        tags.vm.$emit("update:modelValue", ["alpha", "beta", "gamma"]);
        await wrapper.vm.$nextTick();

        expect(model.value).toBe("alpha,beta,gamma");
        expect(wrapper.findComponent(StatelessTags).props("modelValue")).toEqual(["alpha", "beta", "gamma"]);
    });
});
