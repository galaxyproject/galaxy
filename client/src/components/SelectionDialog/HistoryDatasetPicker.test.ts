import { emittedArg, getLocalVue, nth } from "@tests/vitest/helpers";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import type { MyHistory } from "@/api/histories";

import HistoryDatasetPicker from "./HistoryDatasetPicker.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import GTable from "@/components/Common/GTable.vue";
import DataDialogSearch from "@/components/SelectionDialog/DataDialogSearch.vue";

const { server, http } = useServerMock();

const HISTORY: MyHistory = {
    id: "h1",
    name: "Recent History",
    model_class: "History",
    annotation: null,
    archived: false,
    count: 3,
    deleted: false,
    published: false,
    purged: false,
    tags: [],
    update_time: "2026-01-02T00:00:00",
    url: "/api/histories/h1",
    username: "test-user",
};

function interceptHistories() {
    const queries: Record<string, string>[] = [];
    server.use(
        http.get("/api/histories", ({ request, response }) => {
            queries.push(Object.fromEntries(new URL(request.url).searchParams.entries()));
            return response(200).json([HISTORY], { headers: { total_matches: "1" } });
        }),
    );
    return queries;
}

const histories = Array.from({ length: 30 }, (_, index) => ({
    id: `h${index + 1}`,
    name: `history ${index + 1}`,
    count: 2,
    url: `/api/histories/h${index + 1}`,
    tags: [],
    update_time: "2026-10-17T09:30:00",
}));

const datasets = [
    { id: "d1", name: "reads.fastq", url: "/api/datasets/d1", tags: [], update_time: "2026-10-17T09:30:00" },
    { id: "d2", name: "genome.fasta", url: "/api/datasets/d2", tags: [], update_time: "2026-10-17T09:30:00" },
];

function mockApi() {
    const historyQueries: URLSearchParams[] = [];
    const datasetQueries: URLSearchParams[] = [];
    server.use(
        http.untyped.get("/api/histories", ({ request }) => {
            const query = new URL(request.url).searchParams;
            historyQueries.push(query);
            const search = query.get("search");
            const matches = histories.filter((history) => history.name.includes(search ?? ""));
            const offset = Number(query.get("offset"));
            const limit = Number(query.get("limit"));
            // like the API: only a search request counts its matches
            const headers: Record<string, string> = search === null ? {} : { total_matches: `${matches.length}` };
            return HttpResponse.json(matches.slice(offset, offset + limit), { headers });
        }),
        http.untyped.get("/api/datasets", ({ request }) => {
            const query = new URL(request.url).searchParams;
            datasetQueries.push(query);
            const name = query.get("qv") ?? "";
            const matches = datasets.filter((dataset) => dataset.name.includes(name));
            return HttpResponse.json(matches, { headers: { total_matches: `${matches.length}` } });
        }),
    );
    return { historyQueries, datasetQueries };
}

function rowLabels(wrapper: ReturnType<typeof mount>) {
    return wrapper.findAll("td[id^='g-table-cell-label-']").map((cell) => cell.text());
}

async function mountPicker() {
    const wrapper = mount(HistoryDatasetPicker as object, { global: getLocalVue() });
    await flushPromises();
    return wrapper;
}

async function search(wrapper: ReturnType<typeof mount>, text: string) {
    wrapper.findComponent(FilterMenu).vm.$emit("update:filter-text", text);
    await flushPromises();
}

describe("HistoryDatasetPicker", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    it("lists only the user's own histories, most recently updated first", async () => {
        const queries = interceptHistories();

        const wrapper = await mountPicker();

        expect(queries[0]).toMatchObject({
            search: "",
            sort_by: "update_time",
            sort_desc: "true",
            show_own: "true",
            show_published: "false",
            show_shared: "false",
            show_archived: "false",
        });
        expect(wrapper.text()).toContain("Recent History");
    });

    it("pages the searched histories on the server", async () => {
        const { historyQueries } = mockApi();
        const wrapper = await mountPicker();
        expect(rowLabels(wrapper)).toHaveLength(25);
        expect(nth(historyQueries, 0).get("offset")).toBe("0");
        expect(nth(historyQueries, 0).get("limit")).toBe("25");

        await search(wrapper, "history");
        await wrapper.find("[aria-label='Go to page 2']").trigger("click");
        await flushPromises();
        expect(nth(historyQueries, -1).get("offset")).toBe("25");
        expect(rowLabels(wrapper)).toEqual(["history 26", "history 27", "history 28", "history 29", "history 30"]);
    });

    it("sorts the histories newest first until a column is sorted", async () => {
        const { historyQueries } = mockApi();
        const wrapper = await mountPicker();
        await search(wrapper, "history");
        expect(nth(historyQueries, -1).get("sort_by")).toBe("update_time");
        expect(nth(historyQueries, -1).get("sort_desc")).toBe("true");

        wrapper.findComponent(GTable).vm.$emit("sort-changed", "label", false);
        await flushPromises();
        expect(nth(historyQueries, -1).get("sort_by")).toBe("name");
        expect(nth(historyQueries, -1).get("sort_desc")).toBe("false");
    });

    it("sorts the datasets by update time when Last Updated is sorted", async () => {
        const { datasetQueries } = mockApi();
        const wrapper = await mountPicker();
        await nth(wrapper.findAll("button.selection-dialog-folder"), 0).trigger("click");
        await flushPromises();

        wrapper.findComponent(GTable).vm.$emit("sort-changed", "update_time", true);
        await flushPromises();
        expect(nth(datasetQueries, -1).get("order")).toBe("update_time-dsc");
    });

    it("searches the histories on the server from page 1", async () => {
        const { historyQueries } = mockApi();
        const wrapper = await mountPicker();
        await search(wrapper, "history");
        await wrapper.find("[aria-label='Go to page 2']").trigger("click");
        await flushPromises();
        const loadsBefore = historyQueries.length;

        await search(wrapper, "history 1");
        expect(historyQueries.length).toBe(loadsBefore + 1);
        expect(nth(historyQueries, -1).get("search")).toBe("history 1");
        expect(nth(historyQueries, -1).get("offset")).toBe("0");
        expect(rowLabels(wrapper)).toHaveLength(11);
    });

    it("opens a history, searches and selects its datasets, and returns them on OK", async () => {
        const { datasetQueries } = mockApi();
        const wrapper = await mountPicker();

        await nth(wrapper.findAll("button.selection-dialog-folder"), 1).trigger("click");
        await flushPromises();
        expect(nth(datasetQueries, -1).get("history_id")).toBe("h2");
        expect(rowLabels(wrapper)).toEqual(["reads.fastq", "genome.fasta"]);

        wrapper.findComponent(DataDialogSearch).vm.$emit("input", "genome");
        await flushPromises();
        expect(nth(datasetQueries, -1).get("qv")).toBe("genome");
        expect(rowLabels(wrapper)).toEqual(["genome.fasta"]);

        await wrapper.find("tbody tr[aria-rowindex='1']").trigger("click");
        const ok = wrapper.get("[data-description='selection dialog ok']");
        expect(ok.text()).toContain("Select 1 dataset");

        await ok.trigger("click");
        const selected = emittedArg(wrapper, "onSelect") as { id: string }[];
        expect(selected.map((item) => item.id)).toEqual(["d2"]);
    });

    it("clears the dataset selection when going back to the histories", async () => {
        mockApi();
        const wrapper = await mountPicker();
        await nth(wrapper.findAll("button.selection-dialog-folder"), 0).trigger("click");
        await flushPromises();
        await wrapper.find("tbody tr[aria-rowindex='1']").trigger("click");
        expect(wrapper.get("[data-description='selection dialog ok']").text()).toContain("Select 1 dataset");

        await wrapper.get("[data-description='selection dialog undo']").trigger("click");
        await flushPromises();
        expect(rowLabels(wrapper)).toHaveLength(25);
        const ok = wrapper.get("[data-description='selection dialog ok']");
        expect(ok.classes()).toContain("g-disabled");
        expect(ok.text()).not.toContain("dataset");
    });
});
