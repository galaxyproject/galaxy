import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import FormCollectionType from "./FormCollectionType.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import FormSelect from "@/components/Form/Elements/FormSelect.vue";
import FormElement from "@/components/Form/FormElement.vue";

const localVue = getLocalVue();

function mountWithValue(value?: string): VueWrapper {
    return mount(FormCollectionType as object, {
        propsData: { value },
        localVue,
        pinia: createTestingPinia({ createSpy: vi.fn }),
    });
}

function element(wrapper: VueWrapper) {
    return wrapper.findComponent(FormElement);
}

function renderedSelection(wrapper: VueWrapper) {
    return wrapper.find("#form-element-collection_type [data-selected-value]").attributes("data-selected-value");
}

function customField(wrapper: VueWrapper) {
    return wrapper.find("#collection_type-other");
}

function emittedTypes(wrapper: VueWrapper) {
    return (wrapper.emitted("onChange") ?? []).map((args) => args[0]);
}

describe("FormCollectionType", () => {
    it("selects a known collection type and describes it", () => {
        const wrapper = mountWithValue("list:paired");
        expect(renderedSelection(wrapper)).toBe("list:paired");
        expect(wrapper.find("#form-element-collection_type").text()).toContain("forward and reverse pair");
        expect(customField(wrapper).exists()).toBe(false);
    });

    it("warns when no collection type is set", () => {
        const wrapper = mountWithValue(undefined);
        expect(renderedSelection(wrapper)).toBe("Any collection type");
        expect(element(wrapper).props("warning")).toBeTruthy();
    });

    it("treats an empty collection type as any collection type", () => {
        const wrapper = mountWithValue("");
        expect(renderedSelection(wrapper)).toBe("Any collection type");
    });

    it("shows a collection type the select doesn't know as a custom type", () => {
        const wrapper = mountWithValue("list:list:list");
        expect(renderedSelection(wrapper)).toBe("__other__");
        expect((customField(wrapper).element as HTMLInputElement).value).toBe("list:list:list");
    });

    it("doesn't describe the saved type under an unsaved custom one", async () => {
        const wrapper = mountWithValue("list:paired");
        wrapper.findComponent(FormSelect).vm.$emit("input", "__other__");
        await wrapper.vm.$nextTick();
        await customField(wrapper).setValue("list:lsit");
        expect(wrapper.find("#form-element-collection_type").text()).not.toContain("forward and reverse pair");
    });

    it("emits a collection type picked from the select", async () => {
        const wrapper = mountWithValue("list");
        wrapper.findComponent(FormSelect).vm.$emit("input", "sample_sheet:paired");
        await wrapper.vm.$nextTick();
        expect(emittedTypes(wrapper)).toEqual(["sample_sheet:paired"]);
    });

    it("emits null when any collection type is picked", async () => {
        // null keeps the key in the saved tool state; without it the server defaults to "list"
        const wrapper = mountWithValue("list");
        wrapper.findComponent(FormSelect).vm.$emit("input", null);
        await wrapper.vm.$nextTick();
        expect(emittedTypes(wrapper)).toEqual([null]);
    });

    it("emits a valid custom collection type", async () => {
        const wrapper = mountWithValue("list:list:list");
        await customField(wrapper).setValue("list:list:paired");
        expect(emittedTypes(wrapper)).toEqual(["list:list:paired"]);
    });

    it("flags an invalid custom collection type without emitting it", async () => {
        const wrapper = mountWithValue("list:list:list");
        await customField(wrapper).setValue("list:lsit");
        expect(emittedTypes(wrapper)).toEqual([]);
        expect(wrapper.find("#form-element-collection_type").text()).toContain("Invalid collection type");
    });

    it("asks for a collection type when the custom field is cleared", async () => {
        const wrapper = mountWithValue("list:list:list");
        await customField(wrapper).setValue("");
        expect(emittedTypes(wrapper)).toEqual([]);
        expect(wrapper.find("#form-element-collection_type").text()).toContain(
            "Enter a collection type such as list:list:paired.",
        );
    });

    it("picks a collection type from the help dialog", async () => {
        const wrapper = mountWithValue("list:list:list");
        expect(wrapper.findComponent(GModal).props("show")).toBe(false);
        await wrapper.find("[data-description='collection type help']").trigger("click");
        expect(wrapper.findComponent(GModal).props("show")).toBe(true);

        await wrapper.find("[data-collection-type='list:paired_or_unpaired']").trigger("click");
        expect(emittedTypes(wrapper)).toEqual(["list:paired_or_unpaired"]);
        expect(wrapper.findComponent(GModal).props("show")).toBe(false);

        await wrapper.setProps({ value: "list:paired_or_unpaired" });
        expect(renderedSelection(wrapper)).toBe("list:paired_or_unpaired");
        expect(customField(wrapper).exists()).toBe(false);
    });
});
