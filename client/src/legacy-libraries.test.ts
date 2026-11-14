import { mount } from "@vue/test-utils";
import { BButton, BCol, BFormGroup, BFormTextarea, BRow } from "bootstrap-vue";
import { describe, expect, it } from "vitest";
import { defineComponent, nextTick } from "vue";

import { LEGACY_COMPAT_CONFIG } from "./legacy-libraries";

import FormText from "@/components/Form/Elements/FormText.vue";

function compatConfigOf(component: any) {
    return (component.options ?? component).compatConfig;
}

describe("legacy-libraries marker", () => {
    it("marks bootstrap-vue's extended and plain-object components", () => {
        for (const component of [BButton, BFormTextarea, BCol, BFormGroup, BRow]) {
            expect(compatConfigOf(component)).toBe(LEGACY_COMPAT_CONFIG);
        }
    });

    // compat-config.js turns COMPONENT_V_MODEL and ATTR_FALSE_VALUE off, so
    // without the marker BFormTextarea's v-model would bind modelValue against
    // its value/input model and BButton would render disabled="false". The
    // FormText next to them checks that Galaxy's own components still get the
    // Vue 3 modelValue contract, i.e. the marker stays on bootstrap-vue.
    it("keeps bootstrap-vue's v-model and attributes working with Galaxy's flags off", async () => {
        const Parent = defineComponent({
            components: { BButton, BFormTextarea, FormText },
            data: () => ({ text: "start", galaxyText: "galaxy start" }),
            template: `<div>
                <BFormTextarea v-model="text" />
                <BButton :disabled="false">Go</BButton>
                <FormText v-model="galaxyText" />
            </div>`,
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

        const formText = wrapper.findComponent(FormText);
        expect(formText.props("modelValue")).toBe("galaxy start");
        const input = formText.find("input");
        expect((input.element as HTMLInputElement).value).toBe("galaxy start");
        await input.setValue("galaxy typed");
        expect(formText.emitted("update:modelValue")?.at(-1)).toEqual(["galaxy typed"]);
        expect((wrapper.vm as any).galaxyText).toBe("galaxy typed");
    });
});
