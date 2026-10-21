import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import type { VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { HDASummary } from "@/api";
import { Toast } from "@/composables/toast";

import * as PairCollectionCreatorStories from "./PairCollectionCreator.stories";
import { changeHistory } from "./test-utils";

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

async function clickDataset(wrapper: VueWrapper, id: string) {
    const view = wrapper
        .findAllComponents(DatasetCollectionElementView)
        .find((candidate) => (candidate.props("element") as HDASummary).id === id);
    view?.vm.$emit("element-is-selected", view.props("element"));
    await flushPromises();
}

// Each side's content and the toast's text are checked in the stories' play functions; a role
// can't tell an error toast from a warning, so the variant stays here.
describe("PairCollectionCreator", () => {
    it.each([
        ["left the history", `Delete ${REVERSE.name}`, "2: SRR1553425_2 has been removed from the collection"],
        [
            "is no longer usable",
            `Fail ${REVERSE.name}`,
            "2: SRR1553425_2 has errored, is paused, or is not accessible and is not a valid element for this collection",
        ],
    ])("raises an error when a picked dataset %s", async (_change, control, message) => {
        const wrapper = await mountCreator();

        await clickDataset(wrapper, FORWARD.id);
        await clickDataset(wrapper, REVERSE.id);

        await changeHistory(wrapper, control);

        expect(toastError).toHaveBeenCalledTimes(1);
        expect(toastError).toHaveBeenCalledWith(message, "Invalid element");
    });
});
