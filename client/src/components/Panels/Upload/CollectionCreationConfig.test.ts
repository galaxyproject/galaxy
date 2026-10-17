import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { CollectionCreationState } from "@/composables/upload/collectionTypes";

import CollectionCreationConfig from "./CollectionCreationConfig.vue";
import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";
import GSelect from "@/components/BaseComponents/GSelect.vue";

const globalConfig = getLocalVue();

function mountConfig(files = [{ name: "a_1.fq" }, { name: "a_2.fq" }]) {
    return mount(CollectionCreationConfig, {
        props: { files },
        global: { ...globalConfig, stubs: { ...globalConfig.stubs, FontAwesomeIcon: true } },
    });
}

function lastState(wrapper: ReturnType<typeof mountConfig>) {
    const states = wrapper.emitted("update:state") as CollectionCreationState[][];
    return states[states.length - 1]![0]!;
}

describe("CollectionCreationConfig", () => {
    it("shows the collection settings once the switch is turned on", async () => {
        const wrapper = mountConfig();
        const toggle = wrapper.findComponent(GCheckbox);

        expect(toggle.find("input").attributes("role")).toBe("switch");
        expect(wrapper.find("#collection-type-select").exists()).toBe(false);

        await toggle.find("input").setValue(true);

        expect(lastState(wrapper).validation.isActive).toBe(true);
        expect(wrapper.find("#collection-type-select").exists()).toBe(true);
    });

    it("emits the collection type picked in the select", async () => {
        const wrapper = mountConfig();
        await wrapper.find('[data-test-id="collection-toggle"] input').setValue(true);
        await wrapper.find("#collection-name-input").setValue("pairs");

        const select = wrapper.findComponent(GSelect);
        expect(select.element.tagName).toBe("SELECT");
        expect(select.attributes("id")).toBe("collection-type-select");

        await select.setValue("list:paired");

        expect(lastState(wrapper).config).toEqual({ name: "pairs", type: "list:paired" });
    });
});
