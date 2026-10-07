import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import FormCollectionType from "./FormCollectionType.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import FormElement from "@/components/Form/FormElement.vue";

const localVue = getLocalVue();

function mountWithValue(value?: string): VueWrapper {
    return mount(FormCollectionType as object, {
        propsData: { value },
        localVue,
        pinia: createTestingPinia({ createSpy: vi.fn }),
    });
}

function field(wrapper: VueWrapper, id: string) {
    return wrapper.findAllComponents(FormElement).find((element) => element.props("id") === id);
}

function renderedSelection(wrapper: VueWrapper) {
    return wrapper.find("#form-element-collection_type [data-selected-value]").attributes("data-selected-value");
}

function emittedTypes(wrapper: VueWrapper) {
    return (wrapper.emitted("onChange") ?? []).map((args) => args[0]);
}

describe("FormCollectionType", () => {
    it("selects a known collection type and describes it", () => {
        const wrapper = mountWithValue("list:paired");
        const select = field(wrapper, "collection_type")!;
        expect(select.props("value")).toBe("list:paired");
        expect(renderedSelection(wrapper)).toBe("list:paired");
        expect(select.props("help")).toContain("forward and reverse pair");
        expect(field(wrapper, "collection_type_custom")).toBeUndefined();
    });

    it("warns when no collection type is set", () => {
        const wrapper = mountWithValue(undefined);
        const select = field(wrapper, "collection_type")!;
        expect(select.props("value")).toBeNull();
        expect(renderedSelection(wrapper)).toBe("Any collection type");
        expect(select.props("warning")).toBeTruthy();
    });

    it("shows a collection type the select doesn't know as a custom type", () => {
        const wrapper = mountWithValue("list:list:list");
        expect(renderedSelection(wrapper)).toBe("__custom__");
        expect(field(wrapper, "collection_type_custom")!.props("value")).toBe("list:list:list");
    });

    it("emits a collection type picked from the select", async () => {
        const wrapper = mountWithValue("list");
        field(wrapper, "collection_type")!.vm.$emit("input", "sample_sheet:paired");
        await wrapper.vm.$nextTick();
        expect(emittedTypes(wrapper)).toEqual(["sample_sheet:paired"]);
    });

    it("emits null when any collection type is picked", async () => {
        // null keeps the key in the saved tool state; without it the server defaults to "list"
        const wrapper = mountWithValue("list");
        field(wrapper, "collection_type")!.vm.$emit("input", null);
        await wrapper.vm.$nextTick();
        expect(emittedTypes(wrapper)).toEqual([null]);
    });

    it("treats an empty collection type as any collection type", () => {
        const wrapper = mountWithValue("");
        expect(renderedSelection(wrapper)).toBe("Any collection type");
    });

    it("doesn't emit a cleared custom collection type", async () => {
        const wrapper = mountWithValue("list:list:list");
        field(wrapper, "collection_type_custom")!.vm.$emit("input", "");
        await wrapper.vm.$nextTick();
        expect(field(wrapper, "collection_type_custom")!.props("error")).toBeTruthy();
        expect(emittedTypes(wrapper)).toEqual([]);
    });

    it("switches to a text field for a custom collection type", async () => {
        const wrapper = mountWithValue("list");
        field(wrapper, "collection_type")!.vm.$emit("input", "__custom__");
        await wrapper.vm.$nextTick();
        expect(emittedTypes(wrapper)).toEqual([]);

        const custom = field(wrapper, "collection_type_custom")!;
        expect(custom.props("value")).toBe("list");
        custom.vm.$emit("input", "list:list:paired");
        await wrapper.vm.$nextTick();
        expect(emittedTypes(wrapper)).toEqual(["list:list:paired"]);
    });

    it("keeps the custom text field while a typed value passes through a known type", async () => {
        const wrapper = mountWithValue("list:list:list");
        field(wrapper, "collection_type_custom")!.vm.$emit("input", "list");
        await wrapper.setProps({ value: "list" });
        expect(field(wrapper, "collection_type_custom")!.props("value")).toBe("list");
        expect(emittedTypes(wrapper)).toEqual(["list"]);
    });

    it("flags an invalid custom collection type without emitting it", async () => {
        const wrapper = mountWithValue("list:list:list");
        field(wrapper, "collection_type_custom")!.vm.$emit("input", "list:lsit");
        await wrapper.vm.$nextTick();
        expect(field(wrapper, "collection_type_custom")!.props("error")).toBe("Invalid collection type");
        expect(emittedTypes(wrapper)).toEqual([]);
    });

    it("picks a collection type from the help dialog", async () => {
        const wrapper = mountWithValue("list:list:list");
        expect(wrapper.findComponent(GModal).props("show")).toBe(false);
        await wrapper.find("[data-description='collection type help']").trigger("click");
        expect(wrapper.findComponent(GModal).props("show")).toBe(true);

        await wrapper.find("[data-collection-type='list:paired_or_unpaired']").trigger("click");
        expect(emittedTypes(wrapper)).toEqual(["list:paired_or_unpaired"]);
        expect(wrapper.findComponent(GModal).props("show")).toBe(false);
        expect(field(wrapper, "collection_type")!.props("value")).toBe("list:paired_or_unpaired");
        expect(field(wrapper, "collection_type_custom")).toBeUndefined();
    });
});
