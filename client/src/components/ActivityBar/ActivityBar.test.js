import { composeStories } from "@storybook/vue3-vite";
import { dispatchEvent, emittedArg } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { disposePinia, getActivePinia } from "pinia";
import { describe, expect, it, onTestFinished, vi } from "vitest";

import SortableList from "@/components/Common/SortableList";
import { OWN_WORKFLOW } from "@/components/Workflow/test_fixtures";
import { useActivityStore } from "@/stores/activityStore";
import { useConfigStore } from "@/stores/configurationStore";
import { useEventStore } from "@/stores/eventStore";

import * as ActivityBarStories from "./ActivityBar.stories";

import ActivityBar from "./ActivityBar.vue";

const stories = composeStories(ActivityBarStories);
const mountStory = useStoryMount();
const scope = ActivityBarStories.default.args.activityBarId;

async function mountBar(story = stories.InteractiveToolsEnabled) {
    const wrapper = mountStory(story);
    const pinia = getActivePinia();
    onTestFinished(() => disposePinia(pinia));
    await vi.waitFor(() => {
        expect(useConfigStore().isLoaded).toBe(true);
        expect(wrapper.findComponent(ActivityBar).exists()).toBe(true);
    });
    // ActivityBar updates its defaults through the store's existing 10ms debounce.
    await useActivityStore(scope).sync();
    await flushPromises();
    return wrapper.getComponent(ActivityBar);
}

describe("ActivityBar", () => {
    it("renders each configured activity", async () => {
        const wrapper = await mountBar();
        const items = wrapper.findAll("#activity-tools, #activity-interactivetools, #activity-workflows");
        expect(items.length).toBe(3);
    });

    it("emits the workflow run destination when a workflow is dragged onto the bar", async () => {
        const wrapper = await mountBar();
        useEventStore().setDragData({
            id: OWN_WORKFLOW.id,
            description: OWN_WORKFLOW.name,
            model_class: "StoredWorkflow",
            name: OWN_WORKFLOW.name,
        });
        const bar = wrapper.get("[data-description='activity bar']");
        dispatchEvent(bar, "dragenter");
        const emittedEvent = emittedArg(wrapper, "dragstart");
        expect(emittedEvent.to).toBe(`/workflows/run?id=${OWN_WORKFLOW.id}`);
    });

    describe("interactivetools visibility", () => {
        it("hides interactivetools activity when interactivetools_enable is false", async () => {
            const testWrapper = await mountBar(stories.InteractiveToolsDisabled);
            expect(testWrapper.findAll("[id='activity-interactivetools']").length).toBe(0);
        });

        it("shows interactivetools activity when interactivetools_enable is true", async () => {
            const testWrapper = await mountBar(stories.InteractiveToolsEnabled);
            expect(testWrapper.findAll("[id='activity-interactivetools']").length).toBe(1);
        });

        it("keeps a hidden interactivetools activity when the visible ones are reordered", async () => {
            const testWrapper = await mountBar(stories.InteractiveToolsDisabled);
            const bar = testWrapper.getComponent(SortableList);
            const visible = bar.props("modelValue");
            expect(visible.map((activity) => activity.id)).toEqual(["tools", "workflows"]);
            bar.vm.$emit("update:modelValue", [...visible].reverse());
            await testWrapper.vm.$nextTick();
            const stored = useActivityStore(scope).activities.map((activity) => activity.id);
            expect(stored).toEqual(["workflows", "tools", "interactivetools"]);
        });
    });
});
