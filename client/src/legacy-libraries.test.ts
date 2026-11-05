import { mount } from "@vue/test-utils";
import { BButton, BCol, BFormGroup, BFormTextarea, BRow } from "bootstrap-vue";
import { describe, expect, it } from "vitest";
import { defineComponent, nextTick } from "vue";

import { LEGACY_COMPAT_CONFIG } from "./legacy-libraries";

function compatConfigOf(component: any) {
    return (component.options ?? component).compatConfig;
}

describe("legacy-libraries marker", () => {
    it("marks bootstrap-vue's extended and plain-object components", () => {
        for (const component of [BButton, BFormTextarea, BCol, BFormGroup, BRow]) {
            expect(compatConfigOf(component)).toBe(LEGACY_COMPAT_CONFIG);
        }
    });

    it("keeps Vue 2 v-model and attribute behavior for bootstrap-vue under a MODE 3 parent", async () => {
        const Parent = defineComponent({
            components: { BButton, BFormTextarea },
            data: () => ({ text: "start" }),
            template: `<div><BFormTextarea v-model="text" /><BButton :disabled="false">Go</BButton></div>`,
        });
        const wrapper = mount(Parent);
        const textarea = wrapper.find("textarea");
        expect((textarea.element as HTMLTextAreaElement).value).toBe("start");

        await textarea.setValue("typed");
        expect((wrapper.vm as any).text).toBe("typed");

        (wrapper.vm as any).text = "from parent";
        await nextTick();
        expect((textarea.element as HTMLTextAreaElement).value).toBe("from parent");

        expect(wrapper.find("button").attributes("disabled")).toBeUndefined();
    });
});
