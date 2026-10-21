import "@/components/Form/Elements/FormSelectMany/worker/__mocks__/selectMany";

import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import type { VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toRaw } from "vue";

import type { HDASummary } from "@/api";
import { Toast } from "@/composables/toast";

import * as ListCollectionCreatorStories from "./ListCollectionCreator.stories";
import { changeHistory } from "./test-utils";

import ListCollectionCreator from "./ListCollectionCreator.vue";
import FormSelectMany from "@/components/Form/Elements/FormSelectMany/FormSelectMany.vue";

vi.mock("@/composables/toast");

const toastError = vi.mocked(Toast.error);

const stories = composeStories(ListCollectionCreatorStories);
const mountStory = useStoryMount();

const [CONTROL, TREATED] = stories.TwoDatasetsInHistory.args.history as [HDASummary, HDASummary];

beforeEach(() => {
    vi.clearAllMocks();
});

async function mountCreator() {
    const wrapper = mountStory(stories.TwoDatasetsInHistory);
    await flushPromises();
    return wrapper;
}

function inListElements(wrapper: VueWrapper): HDASummary[] {
    return wrapper.findComponent(FormSelectMany).props("value") as HDASummary[];
}

function inListIds(wrapper: VueWrapper): string[] {
    return inListElements(wrapper).map((element) => element.id);
}

async function selectIntoList(wrapper: VueWrapper, datasets: HDASummary[]) {
    for (const { name } of datasets) {
        const option = wrapper
            .findAll(".options-list.unselected .option-button")
            .find((candidate) => candidate.attributes("aria-label") === `Select ${name}`);
        if (!option) {
            throw new Error(`No unselected option for "${name}"`);
        }
        await option.trigger("click");
        await flushPromises();
    }
}

// The list's order and the toasts' text are checked in the stories' play functions. Which objects
// the list holds isn't visible, and a role can't tell an error toast from a warning, so those stay.
describe("ListCollectionCreator", () => {
    it("holds the creator's working copies, not the props, after initialElements changes", async () => {
        const wrapper = await mountCreator();

        await selectIntoList(wrapper, [TREATED, CONTROL]);
        expect(inListIds(wrapper)).toEqual([TREATED.id, CONTROL.id]);

        // same datasets, new prop identity (e.g. a history poll tick)
        const creator = wrapper.getComponent(ListCollectionCreator);
        const before = creator.props("initialElements") as HDASummary[];
        await changeHistory(wrapper, "Refresh history");
        const refreshed = creator.props("initialElements") as HDASummary[];
        expect(refreshed[1]).not.toBe(before[1]);

        // the user's order survives, holding the creator's working copies rather than the props
        expect(inListIds(wrapper)).toEqual([TREATED.id, CONTROL.id]);
        expect(toRaw(inListElements(wrapper)[0])).not.toBe(toRaw(refreshed[1]));
    });

    it.each([
        ["left the history", `Delete ${TREATED.name}`, "2: treated has been removed from the collection"],
        [
            "is no longer usable",
            `Fail ${TREATED.name}`,
            "2: treated has errored, is paused, or is not accessible and is not a valid element for this collection",
        ],
    ])("raises an error when a dataset in the list %s", async (_change, historyChange, message) => {
        const wrapper = await mountCreator();

        await selectIntoList(wrapper, [CONTROL, TREATED]);
        expect(inListIds(wrapper)).toEqual([CONTROL.id, TREATED.id]);

        await changeHistory(wrapper, historyChange);

        expect(toastError).toHaveBeenCalledTimes(1);
        expect(toastError).toHaveBeenCalledWith(message, "Invalid element");
    });
});
