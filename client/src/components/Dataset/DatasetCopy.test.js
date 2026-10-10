import { getFakeHistorySummary } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { afterEach, describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { seedCurrentHistory } from "@/stores/testUtils";

import DatasetCopy from "./DatasetCopy.vue";

const { server, http } = useServerMock();
const localVue = getLocalVue();

enableAutoUnmount(afterEach);

const H1 = { id: "h1", name: "H1" };
const H2 = { id: "h2", name: "H2" };

const SELECTORS = {
    COPY_BUTTON: "[data-description='copy button']",
    NEW_HISTORY_NAME: "input[data-description='copy history name']",
    HISTORY_SEARCH_INPUTS: "input.multiselect__input",
    COPIED_TO_LINKS: "[data-description='copy switch history']",
};

function dataset(id, hid, name) {
    return { id, hid, name, history_content_type: "dataset" };
}

/** Serves the history list and the same contents for every history; returns the ids whose contents were requested. */
function serveHistories(histories, contents) {
    const contentsRequests = [];
    server.use(
        http.get("/api/histories", ({ response }) => response(200).json(histories)),
        http.get("/api/histories/{history_id}/contents", ({ params, response }) => {
            contentsRequests.push(params.history_id);
            return response(200).json(contents);
        }),
    );
    return contentsRequests;
}

/** Answers copy requests with the given target history ids; returns each request's source history and body. */
function serveCopy(targetHistoryIds) {
    const copyRequests = [];
    server.use(
        http.post("/api/histories/{history_id}/copy_contents", async ({ params, request, response }) => {
            copyRequests.push({ historyId: params.history_id, body: await request.json() });
            return response(200).json({ history_ids: targetHistoryIds });
        }),
    );
    return copyRequests;
}

/** Mounts the copy form with `currentHistory`, if any, as the current history and waits for the source contents. */
async function mountDatasetCopy({ currentHistory = H1 } = {}) {
    const pinia = createPinia();
    if (currentHistory) {
        seedCurrentHistory(getFakeHistorySummary(currentHistory), pinia);
    }
    const wrapper = mount(DatasetCopy, {
        global: {
            ...withPlugins(localVue, pinia),
            stubs: { ...localVue.stubs, RouterLink: { template: "<a><slot /></a>" } },
        },
    });
    await flushPromises();
    return wrapper;
}

function sourceCheckbox(wrapper, type, id) {
    return wrapper.get(`input[data-description='copy ${type}|${id}']`);
}

function targetHistoryCheckbox(wrapper, name) {
    const targets = wrapper.findAll(".dataset-copy-contents").at(1);
    const label = targets.findAll("label").find((candidate) => candidate.text() === name);
    return targets.get(`input[id='${label.attributes("for")}']`);
}

function buttonByText(wrapper, text) {
    return wrapper.findAll("button").find((button) => button.text() === text);
}

function copiedToLinkTexts(wrapper) {
    return wrapper.findAll(SELECTORS.COPIED_TO_LINKS).map((link) => link.text());
}

async function copySelected(wrapper) {
    await wrapper.get(SELECTORS.COPY_BUTTON).trigger("click");
    await flushPromises();
}

describe("DatasetCopy", () => {
    it("lists the histories and the current history's datasets and collections on mount", async () => {
        const contentsRequests = serveHistories(
            [
                { id: "h1", name: "History One" },
                { id: "h2", name: "History Two" },
            ],
            [dataset("d1", 1, "A"), { id: "d2", hid: 2, name: "B", history_content_type: "collection" }],
        );

        const wrapper = await mountDatasetCopy();

        expect(contentsRequests).toEqual(["h1"]);
        expect(wrapper.text()).toContain("History One");
        expect(wrapper.text()).toContain("History Two");
        expect(wrapper.text()).toContain("1: A");
        expect(wrapper.text()).toContain("2: B");
    });

    it("sources the current history even when it is not listed first", async () => {
        const contentsRequests = serveHistories([H1, H2], [dataset("d1", 1, "X")]);

        await mountDatasetCopy({ currentHistory: H2 });

        expect(contentsRequests).toEqual(["h2"]);
    });

    it.each([
        ["is not listed", { id: "unlisted", name: "Unlisted" }],
        ["is not known", null],
    ])("falls back to the first listed history when the current history %s", async (_, currentHistory) => {
        const contentsRequests = serveHistories([H1, H2], [dataset("d1", 1, "X")]);

        await mountDatasetCopy({ currentHistory });

        expect(contentsRequests).toEqual(["h1"]);
    });

    it("copies the selected items from the source history and reports success", async () => {
        serveHistories([H1], [dataset("d1", 1, "X")]);
        const copyRequests = serveCopy(["h1"]);
        const wrapper = await mountDatasetCopy();

        await sourceCheckbox(wrapper, "dataset", "d1").setValue(true);
        await copySelected(wrapper);

        expect(copyRequests).toEqual([
            {
                historyId: "h1",
                body: {
                    source_content: [{ id: "d1", type: "dataset" }],
                    target_history_ids: [],
                    target_history_name: null,
                },
            },
        ]);
        expect(wrapper.text()).toMatch(/1 item[s]? copied/);
    });

    it("asks for a selection instead of copying when nothing is selected", async () => {
        serveHistories([H1], []);
        const copyRequests = serveCopy(["h1"]);
        const wrapper = await mountDatasetCopy();

        await copySelected(wrapper);

        expect(wrapper.text()).toContain("Please select datasets and collections.");
        expect(copyRequests).toEqual([]);
    });

    it("shows the error message when the copy request fails", async () => {
        serveHistories([H1], [dataset("d1", 1, "X")]);
        server.use(
            http.post("/api/histories/{history_id}/copy_contents", ({ response }) =>
                response(500).json({ err_msg: "Copy failed" }),
            ),
        );
        const wrapper = await mountDatasetCopy();

        await sourceCheckbox(wrapper, "dataset", "d1").setValue(true);
        await copySelected(wrapper);

        expect(wrapper.text()).toContain("Copy failed");
    });

    it("selects and unselects every source item", async () => {
        serveHistories([H1], [dataset("d1", 1, "X"), dataset("d2", 2, "Y")]);
        const wrapper = await mountDatasetCopy();

        await buttonByText(wrapper, "Select All").trigger("click");

        expect(sourceCheckbox(wrapper, "dataset", "d1").element.checked).toBe(true);
        expect(sourceCheckbox(wrapper, "dataset", "d2").element.checked).toBe(true);

        await buttonByText(wrapper, "Unselect All").trigger("click");

        expect(sourceCheckbox(wrapper, "dataset", "d1").element.checked).toBe(false);
        expect(sourceCheckbox(wrapper, "dataset", "d2").element.checked).toBe(false);
    });

    it("names the existing history the items were copied to", async () => {
        serveHistories([H1], [dataset("d1", 1, "X")]);
        serveCopy(["h1"]);
        const wrapper = await mountDatasetCopy();

        await sourceCheckbox(wrapper, "dataset", "d1").setValue(true);
        await copySelected(wrapper);

        expect(wrapper.text()).toMatch(/1 item[s]? copied to/);
        expect(copiedToLinkTexts(wrapper)).toEqual(["H1"]);
    });

    it("copies to every checked target history and names each of them", async () => {
        serveHistories([H1, H2], [dataset("d1", 1, "X")]);
        const copyRequests = serveCopy(["h1", "h2"]);
        const wrapper = await mountDatasetCopy();

        await sourceCheckbox(wrapper, "dataset", "d1").setValue(true);
        await targetHistoryCheckbox(wrapper, "H1").setValue(true);
        await targetHistoryCheckbox(wrapper, "H2").setValue(true);
        await copySelected(wrapper);

        expect(copyRequests[0].body.target_history_ids).toEqual(["h1", "h2"]);
        expect(wrapper.text()).toMatch(/1 item[s]? copied to/);
        expect(copiedToLinkTexts(wrapper)).toEqual(["H1", "H2"]);
    });

    it("copies to a new history and names it in the success message", async () => {
        serveHistories([H1], [dataset("d1", 1, "X")]);
        const copyRequests = serveCopy(["h2"]);
        const wrapper = await mountDatasetCopy();

        await sourceCheckbox(wrapper, "dataset", "d1").setValue(true);
        await wrapper.get(SELECTORS.NEW_HISTORY_NAME).setValue("New History");
        await copySelected(wrapper);

        expect(copyRequests[0].body).toMatchObject({ target_history_ids: [], target_history_name: "New History" });
        expect(wrapper.text()).toContain("1 item copied to");
        expect(copiedToLinkTexts(wrapper)).toEqual(["New History"]);
    });

    it("labels the history search inputs with their visible captions", async () => {
        serveHistories([H1], []);
        const wrapper = await mountDatasetCopy();

        const labels = wrapper.findAll(SELECTORS.HISTORY_SEARCH_INPUTS).map((input) => {
            expect(input.attributes("aria-label")).toBeUndefined();
            return wrapper.find(`label[for="${input.attributes("id")}"]`).text();
        });
        expect(labels).toEqual(["Select a Source History:", "Select a Target History:"]);
    });
});
