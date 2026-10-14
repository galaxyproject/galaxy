import { composeStories } from "@storybook/vue3-vite";
import { getLocalVue, nth } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { SampleSheetColumnDefinitions } from "@/api";
import type { Step } from "@/stores/workflowStepStore";
import { ensureDefined } from "@/utils/assertions";

import * as FormInputCollectionStories from "./FormInputCollection.stories";

import FormCollectionType from "./FormCollectionType.vue";
import FormColumnDefinitions from "./FormColumnDefinitions.vue";
import FormInputCollection from "./FormInputCollection.vue";
import FormElement from "@/components/Form/FormElement.vue";

const stories = composeStories(FormInputCollectionStories);
const mountStory = useStoryMount();
const localVue = getLocalVue();

const CONDITION_COLUMN: SampleSheetColumnDefinitions = [
    { name: "Condition", type: "string", description: "", optional: false },
];

function stepWithCollectionType(collectionType: string | null): Step {
    const step = FormInputCollectionStories.default.args.step;
    return { ...step, tool_state: { ...step.tool_state, collection_type: JSON.stringify(collectionType) } };
}

function lastEmittedState(wrapper: ReturnType<typeof mountCollectionForm>) {
    return nth(wrapper.emitted<[Record<string, unknown>]>("onChange"), -1)[0];
}

function mountCollectionForm(liveStep = false) {
    if (liveStep) {
        // Composed setProps remounts; the stale-echo contract requires the existing component.
        return mount(FormInputCollection, { props: FormInputCollectionStories.default.args, global: localVue });
    }
    const wrapper = mountStory(stories.DatasetList);
    return wrapper.getComponent(FormInputCollection);
}

afterEach(() => {
    if (vi.isFakeTimers()) {
        vi.clearAllTimers();
    }
    vi.useRealTimers();
});
enableAutoUnmount(afterEach);

describe("FormInputCollection", () => {
    it("shows the values stored on the step", () => {
        const wrapper = mountCollectionForm();
        expect(wrapper.getComponent(FormCollectionType).props("value")).toBe("list");
    });

    it("sends a later edit together with an earlier one the step has not echoed yet", async () => {
        const wrapper = mountCollectionForm();
        vi.useFakeTimers();
        wrapper.getComponent(FormCollectionType).vm.$emit("onChange", "sample_sheet:paired");
        await wrapper.vm.$nextTick();
        expect(wrapper.findComponent(FormColumnDefinitions).exists()).toBe(true);

        wrapper.getComponent(FormColumnDefinitions).vm.$emit("onChange", CONDITION_COLUMN);
        vi.advanceTimersByTime(500);
        await wrapper.vm.$nextTick();

        const state = lastEmittedState(wrapper);
        expect(state.collection_type).toBe("sample_sheet:paired");
        expect(state.column_definitions).toEqual(CONDITION_COLUMN);
    });

    it("keeps any collection type in the saved state", async () => {
        const wrapper = mount(FormInputCollection, {
            props: { step: stepWithCollectionType("list"), datatypes: [] },
            global: localVue,
        });
        const select = wrapper.findAllComponents(FormElement).find((field) => field.props("id") === "collection_type");
        select!.vm.$emit("input", null);
        await wrapper.vm.$nextTick();

        // the state is sent as JSON; a dropped key makes the server default to "list"
        const sent = JSON.parse(JSON.stringify(lastEmittedState(wrapper)));
        expect(sent).toHaveProperty("collection_type", null);
    });

    it("keeps the edited value when the step echoes an older one", async () => {
        const wrapper = mountCollectionForm(true);
        wrapper.getComponent(FormCollectionType).vm.$emit("onChange", "sample_sheet");
        wrapper.getComponent(FormCollectionType).vm.$emit("onChange", "sample_sheet:paired");
        await wrapper.setProps({ step: stepWithCollectionType("sample_sheet") });

        expect(wrapper.getComponent(FormCollectionType).props("value")).toBe("sample_sheet:paired");
        const optionalField = wrapper.findAllComponents(FormElement).find((field) => field.props("id") === "optional");
        expect(optionalField).toBeDefined();
        const emittedCount = ensureDefined(wrapper.emitted("onChange")).length;
        ensureDefined(optionalField).vm.$emit("input", true);
        expect(wrapper.emitted("onChange")).toHaveLength(emittedCount + 1);
        expect(lastEmittedState(wrapper)).toMatchObject({
            collection_type: "sample_sheet:paired",
            optional: true,
        });
    });
});
