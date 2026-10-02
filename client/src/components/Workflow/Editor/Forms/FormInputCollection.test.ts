import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";

import FormCollectionType from "./FormCollectionType.vue";
import FormColumnDefinitions from "./FormColumnDefinitions.vue";
import FormInputCollection from "./FormInputCollection.vue";
import FormElement from "@/components/Form/FormElement.vue";

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
        wrapper = shallowMount(FormInputCollection as object, {
            propsData: {
                step: stepWithCollectionType("list"),
                datatypes: [],
            },
            localVue,
        });
    });

    afterEach(() => {
        wrapper.destroy();
        vi.useRealTimers();
    });

    it("shows the values stored on the step", () => {
        expect(wrapper.findComponent(FormCollectionType).props("value")).toBe("list");
    });

    it("sends a later edit together with an earlier one the step has not echoed yet", async () => {
        vi.useFakeTimers();
        wrapper.findComponent(FormCollectionType).vm.$emit("onChange", "sample_sheet:paired");
        await wrapper.vm.$nextTick();
        expect(wrapper.findComponent(FormColumnDefinitions).exists()).toBe(true);

        wrapper.findComponent(FormColumnDefinitions).vm.$emit("onChange", CONDITION_COLUMN);
        vi.advanceTimersByTime(500);
        await wrapper.vm.$nextTick();

        const state = lastEmittedState(wrapper);
        expect(state.collection_type).toBe("sample_sheet:paired");
        expect(state.column_definitions).toEqual(CONDITION_COLUMN);
    });

    it("keeps the edited value when the step echoes an older one", async () => {
        wrapper.findComponent(FormCollectionType).vm.$emit("onChange", "sample_sheet");
        wrapper.findComponent(FormCollectionType).vm.$emit("onChange", "sample_sheet:paired");
        await wrapper.setProps({ step: stepWithCollectionType("sample_sheet") });

        expect(wrapper.findComponent(FormCollectionType).props("value")).toBe("sample_sheet:paired");
        const optionalField = wrapper
            .findAllComponents(FormElement)
            .wrappers.find((field) => field.props("id") === "optional");
        expect(optionalField).toBeDefined();
        const emittedCount = wrapper.emitted("onChange")!.length;
        optionalField!.vm.$emit("input", true);
        expect(wrapper.emitted("onChange")).toHaveLength(emittedCount + 1);
        expect(lastEmittedState(wrapper)).toMatchObject({
            collection_type: "sample_sheet:paired",
            optional: true,
        });
    });
});
