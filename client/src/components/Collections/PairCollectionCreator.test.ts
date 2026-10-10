import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import type { VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { HDASummary } from "@/api";
import { Toast } from "@/composables/toast";

import * as PairCollectionCreatorStories from "./PairCollectionCreator.stories";
import { changeHistory } from "./test-utils";

import FixedIdentifierDatasetCollectionElementView from "./FixedIdentifierDatasetCollectionElementView.vue";
import DatasetCollectionElementView from "./ListDatasetCollectionElementView.vue";

vi.mock("@/composables/toast");

const toastError = vi.mocked(Toast.error);

const stories = composeStories(PairCollectionCreatorStories);
const mountStory = useStoryMount();

const [FORWARD, REVERSE] = stories.ReadPairInHistory.args.history as [HDASummary, HDASummary];

beforeEach(() => {
    vi.clearAllMocks();
});

async function mountCreator() {
    const wrapper = mountStory(stories.ReadPairInHistory);
    await flushPromises();
    return wrapper;
}

/** The forward/reverse slots as ids - an empty slot renders no view at all. */
function pairedIds(wrapper: VueWrapper): string[] {
    return wrapper
        .findAllComponents(FixedIdentifierDatasetCollectionElementView)
        .map((slot) => (slot.props("element") as HDASummary).id);
}

async function clickDataset(wrapper: VueWrapper, id: string) {
    const view = wrapper
        .findAllComponents(DatasetCollectionElementView)
        .find((candidate) => (candidate.props("element") as HDASummary).id === id);
    view?.vm.$emit("element-is-selected", view.props("element"));
    await flushPromises();
}

describe("PairCollectionCreator", () => {
    it("keeps both sides of the pair when initialElements changes", async () => {
        const wrapper = await mountCreator();

        await clickDataset(wrapper, FORWARD.id);
        await clickDataset(wrapper, REVERSE.id);
        expect(pairedIds(wrapper)).toEqual([FORWARD.id, REVERSE.id]);

        // same datasets, new prop identity (e.g. a history poll tick)
        await changeHistory(wrapper, "Refresh history");

        expect(pairedIds(wrapper)).toEqual([FORWARD.id, REVERSE.id]);
        expect(toastError).not.toHaveBeenCalled();
    });

    it("empties the slot whose dataset left the history and says it was removed", async () => {
        const wrapper = await mountCreator();

        await clickDataset(wrapper, FORWARD.id);
        await clickDataset(wrapper, REVERSE.id);

        await changeHistory(wrapper, `Delete ${REVERSE.name}`);

        expect(pairedIds(wrapper)).toEqual([FORWARD.id]);
        expect(toastError).toHaveBeenCalledTimes(1);
        expect(toastError).toHaveBeenCalledWith(
            "2: SRR1553425_2 has been removed from the collection",
            "Invalid element",
        );
    });

    it("empties the slot whose dataset is no longer usable and says why", async () => {
        const wrapper = await mountCreator();

        await clickDataset(wrapper, FORWARD.id);
        await clickDataset(wrapper, REVERSE.id);

        await changeHistory(wrapper, `Fail ${REVERSE.name}`);

        expect(pairedIds(wrapper)).toEqual([FORWARD.id]);
        expect(toastError).toHaveBeenCalledTimes(1);
        expect(toastError).toHaveBeenCalledWith(
            "2: SRR1553425_2 has errored, is paused, or is not accessible and is not a valid element for this collection",
            "Invalid element",
        );
    });
});
