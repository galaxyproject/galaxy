import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";
import Multiselect from "vue-multiselect";

import { useServerMock } from "@/api/client/__mocks__";
import { useEventStore } from "@/stores/eventStore";

import * as SelectionFieldStories from "./SelectionField.stories";
import { CURRENT_HISTORY, HISTORY_DATASETS } from "./test_fixtures";

import SelectionField from "./SelectionField.vue";

const stories = composeStories(SelectionFieldStories);
const mountStory = useStoryMount();
const { server, http } = useServerMock();

const [FORWARD_READS, REVERSE_READS] = HISTORY_DATASETS;

/** Waits out the component's 300 ms search debounce and the search it starts. */
async function waitForDebouncedSearch() {
    await new Promise((resolve) => setTimeout(resolve, 350));
    await flushPromises();
}

/** Mounts a story and waits for the field's first search. */
async function mountSelectionField(story, options) {
    const wrapper = mountStory(story, options);
    await waitForDebouncedSearch();
    return wrapper;
}

/** Records the query parameters of each dataset search; the story still answers. */
function recordDatasetSearches() {
    const searches = [];
    server.use(
        http.get("/api/datasets", ({ query }) => {
            searches.push({ historyId: query.get("history_id"), text: query.get("qv") });
        }),
    );
    return searches;
}

describe("SelectionField", () => {
    it("searches the current history's datasets when the search text changes", async () => {
        const wrapper = await mountSelectionField(stories.NothingSelected);
        const searches = recordDatasetSearches();

        const multiselect = wrapper.findComponent(Multiselect);
        expect(multiselect.exists()).toBe(true);
        multiselect.vm.$emit("search-change", "SRR");
        await waitForDebouncedSearch();

        expect(searches).toContainEqual({ historyId: CURRENT_HISTORY.id, text: "SRR" });
    });

    it("highlights a dragged dataset and emits it as the selection when dropped", async () => {
        const wrapper = await mountSelectionField(stories.NothingSelected);
        const dropZone = wrapper.find("[aria-roledescription='drop zone']");
        useEventStore().setDragData(REVERSE_READS);

        expect(dropZone.classes()).not.toContain("ui-dragover-success");
        await dropZone.trigger("dragenter");
        expect(dropZone.classes()).toContain("ui-dragover-success");
        await dropZone.trigger("drop");
        expect(dropZone.classes()).not.toContain("ui-dragover-success");
        expect(wrapper.getComponent(SelectionField).emitted("change")).toEqual([
            [{ id: REVERSE_READS.id, name: REVERSE_READS.name }],
        ]);
    });

    it("searches with the custom objectQuery function when provided", async () => {
        const objectQuery = vi.fn(stories.WorkflowLabels.args.objectQuery);
        const wrapper = await mountSelectionField(stories.WorkflowLabels, { props: { objectQuery } });

        wrapper.findComponent(Multiselect).vm.$emit("search-change", "reads");
        await waitForDebouncedSearch();

        expect(objectQuery).toHaveBeenCalledWith("reads");
    });

    it("gives the picker the first dataset, with its id, when no objectId and objectName are given", async () => {
        const wrapper = await mountSelectionField(stories.NothingSelected);

        const multiselect = wrapper.findComponent(Multiselect);
        expect(multiselect.exists()).toBe(true);
        expect(multiselect.props("modelValue")).toEqual({ id: FORWARD_READS.id, name: FORWARD_READS.name });
    });
});
