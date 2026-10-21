import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import * as DatasetCopyStories from "./DatasetCopy.stories";
import { FORWARD_READS, PAIRED_READS, RNA_SEQ, VARIANT_CALLING } from "./test_fixtures";

import DatasetCopy from "./DatasetCopy.vue";

const stories = composeStories(DatasetCopyStories);
const mountStory = useStoryMount();
const { server, http } = useServerMock();

const SELECTORS = {
    COPY_BUTTON: "[data-description='copy button']",
    NEW_HISTORY_NAME: "input[data-description='copy history name']",
    HISTORY_SEARCH_INPUTS: "input.multiselect__input",
    COPIED_TO_LINKS: "[data-description='copy switch history']",
};

/** Records the histories whose contents are requested and each copy request; the story still answers. */
function recordRequests() {
    const contentsRequests = [];
    const copyRequests = [];
    server.use(
        http.get("/api/histories/{history_id}/contents", ({ params }) => {
            contentsRequests.push(params.history_id);
        }),
        http.post("/api/histories/{history_id}/copy_contents", async ({ params, request }) => {
            copyRequests.push({ historyId: params.history_id, body: await request.clone().json() });
        }),
    );
    return { contentsRequests, copyRequests };
}

/** Mounts a story and waits for the source history's contents. */
async function mountDatasetCopy(story) {
    const wrapper = mountStory(story);
    const requests = recordRequests();
    await flushPromises();
    return { wrapper, ...requests };
}

function sourceCheckbox(wrapper, item) {
    return wrapper.get(`input[data-description='copy ${item.history_content_type}|${item.id}']`);
}

function targetHistoryCheckbox(wrapper, name) {
    const targets = wrapper.findAll(".dataset-copy-contents").at(1);
    const label = targets.findAll("label").find((candidate) => candidate.text() === name);
    return label.get("input[type=checkbox]");
}

function copiedToLinkTexts(wrapper) {
    return wrapper.findAll(SELECTORS.COPIED_TO_LINKS).map((link) => link.text());
}

async function copySelected(wrapper) {
    await wrapper.get(SELECTORS.COPY_BUTTON).trigger("click");
    await flushPromises();
}

describe("DatasetCopy", () => {
    it("loads the current history's contents on mount", async () => {
        const { contentsRequests } = await mountDatasetCopy(stories.CopyFromCurrentHistory);

        expect(contentsRequests).toEqual([RNA_SEQ.id]);
    });

    it("sources the current history even when it is not listed first", async () => {
        const { contentsRequests } = await mountDatasetCopy(stories.CurrentHistoryListedSecond);

        expect(contentsRequests).toEqual([VARIANT_CALLING.id]);
    });

    it.each([
        ["is not listed", stories.CurrentHistoryNotListed],
        ["is not known", stories.NoCurrentHistory],
    ])("falls back to the first listed history when the current history %s", async (_, story) => {
        const { contentsRequests } = await mountDatasetCopy(story);

        expect(contentsRequests).toEqual([RNA_SEQ.id]);
    });

    it("copies the selected items from the source history and reports success", async () => {
        // Galaxy refuses a copy with no target; this story accepts it, as this case always expected.
        const { wrapper, copyRequests } = await mountDatasetCopy(stories.NoTargetCopiesIntoSource);

        await sourceCheckbox(wrapper, FORWARD_READS).setValue(true);
        await sourceCheckbox(wrapper, PAIRED_READS).setValue(true);
        await copySelected(wrapper);

        expect(copyRequests).toEqual([
            {
                historyId: RNA_SEQ.id,
                body: {
                    source_content: [
                        { id: FORWARD_READS.id, type: "dataset" },
                        { id: PAIRED_READS.id, type: "dataset_collection" },
                    ],
                    target_history_ids: [],
                    target_history_name: null,
                },
            },
        ]);
        expect(wrapper.text()).toContain("2 items copied to:");
    });

    it("asks for a selection instead of copying when nothing is selected", async () => {
        const { wrapper, copyRequests } = await mountDatasetCopy(stories.EmptyCurrentHistory);

        await copySelected(wrapper);

        expect(wrapper.text()).toContain("Please select datasets and collections.");
        expect(copyRequests).toEqual([]);
    });

    it("names the existing history the items were copied to", async () => {
        // Galaxy refuses a copy with no target; this story accepts it, as this case always expected.
        const { wrapper } = await mountDatasetCopy(stories.NoTargetCopiesIntoSource);

        await sourceCheckbox(wrapper, FORWARD_READS).setValue(true);
        await copySelected(wrapper);

        expect(wrapper.text()).toContain("1 item copied to:");
        expect(copiedToLinkTexts(wrapper)).toEqual([RNA_SEQ.name]);
    });

    it("copies to every checked target history and names each of them", async () => {
        const { wrapper, copyRequests } = await mountDatasetCopy(stories.CopyFromCurrentHistory);

        await sourceCheckbox(wrapper, FORWARD_READS).setValue(true);
        await targetHistoryCheckbox(wrapper, RNA_SEQ.name).setValue(true);
        await targetHistoryCheckbox(wrapper, VARIANT_CALLING.name).setValue(true);
        await copySelected(wrapper);

        expect(copyRequests[0].body.target_history_ids).toEqual([RNA_SEQ.id, VARIANT_CALLING.id]);
        expect(copiedToLinkTexts(wrapper)).toEqual([RNA_SEQ.name, VARIANT_CALLING.name]);
    });

    it("copies to a new history and names it in the success message", async () => {
        const { wrapper, copyRequests } = await mountDatasetCopy(stories.CopyFromCurrentHistory);

        await sourceCheckbox(wrapper, FORWARD_READS).setValue(true);
        await wrapper.get(SELECTORS.NEW_HISTORY_NAME).setValue("Reads for variant calling");
        await copySelected(wrapper);

        expect(copyRequests[0].body).toMatchObject({
            target_history_ids: [],
            target_history_name: "Reads for variant calling",
        });
        expect(copiedToLinkTexts(wrapper)).toEqual(["Reads for variant calling"]);
    });

    it("clears the target history selections when a new history name is typed", async () => {
        const { wrapper } = await mountDatasetCopy(stories.CopyFromCurrentHistory);
        await sourceCheckbox(wrapper, FORWARD_READS).setValue(true);
        const targetCheckbox = targetHistoryCheckbox(wrapper, VARIANT_CALLING.name);
        await targetCheckbox.setValue(true);
        expect(targetCheckbox.element.checked).toBe(true);
        const nameInput = wrapper.get(SELECTORS.NEW_HISTORY_NAME);
        expect(nameInput.classes()).toContain("g-form-input");
        await nameInput.setValue("New History");
        expect(targetCheckbox.element.checked).toBe(false);
    });

    it("labels the history search inputs with their visible captions", async () => {
        const { wrapper } = await mountDatasetCopy(stories.CopyFromCurrentHistory);

        const labels = wrapper.findAll(SELECTORS.HISTORY_SEARCH_INPUTS).map((input) => {
            expect(input.attributes("aria-label")).toBeUndefined();
            return wrapper.find(`label[for="${input.attributes("id")}"]`).text();
        });
        expect(labels).toEqual(["Select a Source History:", "Select a Target History:"]);
    });
});

it("keeps the selection hook on the content checkbox input", async () => {
    const { wrapper } = await mountDatasetCopy(stories.CopyFromCurrentHistory);
    await sourceCheckbox(wrapper, FORWARD_READS).setValue(true);
    const checkbox = wrapper.get(`[data-description='copy dataset|${FORWARD_READS.id}']`);
    expect(checkbox.element.tagName).toBe("INPUT");
    expect(checkbox.element.checked).toBe(true);
});

it("clears the new history name when a target history is checked", async () => {
    const { wrapper } = await mountDatasetCopy(stories.CopyFromCurrentHistory);
    await sourceCheckbox(wrapper, FORWARD_READS).setValue(true);
    const nameInput = wrapper.find(SELECTORS.NEW_HISTORY_NAME);
    await nameInput.setValue("New History");
    await targetHistoryCheckbox(wrapper, VARIANT_CALLING.name).setValue(true);
    expect(nameInput.element.value).toBe("");
    expect(wrapper.getComponent(DatasetCopy).vm.targetMultiSelections).toEqual({ [VARIANT_CALLING.id]: true });
});
