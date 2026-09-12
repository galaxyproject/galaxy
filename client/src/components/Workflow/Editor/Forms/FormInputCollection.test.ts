import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";

import FormInputCollection from "./FormInputCollection.vue";

function stubComponent(name: string, props: string[]) {
    return { default: { name, props, render: (h: (tag: string) => unknown) => h("div") } };
}

vi.mock("@/components/Form/FormElement.vue", () => stubComponent("FormElement", ["id", "value"]));
vi.mock("./FormCollectionType.vue", () => stubComponent("FormCollectionType", ["value", "optional"]));
vi.mock("./FormColumnDefinitions.vue", () => stubComponent("FormColumnDefinitions", ["value", "collectionType"]));
vi.mock("./FormDatatype.vue", () => stubComponent("FormDatatype", ["id", "value", "datatypes"]));
vi.mock("./FormRecordFieldDefinitions.vue", () => stubComponent("FormRecordFieldDefinitions", ["value"]));

const localVue = getLocalVue();

const CONDITION_COLUMN = [{ name: "Condition", type: "string", description: "", optional: false }];

function stepWithCollectionType(collectionType: string | null) {
    return {
        id: 3,
        type: "data_collection_input",
        tool_state: {
            collection_type: JSON.stringify(collectionType),
            optional: "false",
            tag: "null",
            format: "null",
            fields: "null",
            column_definitions: "null",
        },
    };
}

function lastEmittedState(wrapper: Wrapper<Vue>) {
    const emitted = wrapper.emitted("onChange");
    return emitted?.[emitted.length - 1]?.[0];
}

describe("FormInputCollection", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(() => {
        wrapper = mount(FormInputCollection as object, {
            propsData: {
                step: stepWithCollectionType("list"),
                datatypes: [],
            },
            localVue,
        });
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("shows the values stored on the step", () => {
        expect(wrapper.findComponent({ name: "FormCollectionType" }).props("value")).toBe("list");
    });

    it("sends a later edit together with an earlier one the step has not echoed yet", async () => {
        vi.useFakeTimers();
        wrapper.findComponent({ name: "FormCollectionType" }).vm.$emit("onChange", "sample_sheet:paired");
        await wrapper.vm.$nextTick();
        expect(wrapper.findComponent({ name: "FormColumnDefinitions" }).exists()).toBe(true);

        wrapper.findComponent({ name: "FormColumnDefinitions" }).vm.$emit("onChange", CONDITION_COLUMN);
        vi.advanceTimersByTime(500);
        await wrapper.vm.$nextTick();

        const state = lastEmittedState(wrapper);
        expect(state.collection_type).toBe("sample_sheet:paired");
        expect(state.column_definitions).toEqual(CONDITION_COLUMN);
    });

    it("keeps the edited value when the step echoes an older one", async () => {
        wrapper.findComponent({ name: "FormCollectionType" }).vm.$emit("onChange", "sample_sheet");
        wrapper.findComponent({ name: "FormCollectionType" }).vm.$emit("onChange", "sample_sheet:paired");
        await wrapper.setProps({ step: stepWithCollectionType("sample_sheet") });

        expect(wrapper.findComponent({ name: "FormCollectionType" }).props("value")).toBe("sample_sheet:paired");
        const optionalField = wrapper
            .findAllComponents({ name: "FormElement" })
            .wrappers.find((field) => field.props("id") === "optional");
        optionalField?.vm.$emit("input", true);
        expect(lastEmittedState(wrapper).collection_type).toBe("sample_sheet:paired");
    });
});
