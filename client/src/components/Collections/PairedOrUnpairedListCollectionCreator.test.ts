import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import type { HDASummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";

import PairedOrUnpairedListCollectionCreator from "./PairedOrUnpairedListCollectionCreator.vue";

const localVue = getLocalVue(true);

vi.mock("@/composables/useAgGrid", () => ({
    useAgGrid: () => ({
        gridApi: ref(null),
        AgGridVue: {
            name: "AgGridVue",
            props: ["rowData"],
            render(h: (tag: string, data: unknown, children: unknown) => unknown) {
                const self = this as unknown as { rowData: { id: string }[] };
                return h(
                    "div",
                    {},
                    (self.rowData || []).map((row) =>
                        h("div", { class: "grid-row", attrs: { "data-row-id": row.id } }, []),
                    ),
                );
            },
        },
        onGridReady: () => {},
        theme: "ag-theme-alpine",
    }),
}));

const { server, http } = useServerMock();
beforeEach(() => {
    server.use(
        http.get("/api/configuration", ({ response }) => response(200).json({})),
        http.get("/api/genomes", ({ response }) => response(200).json([])),
    );
});

function buildFakeDataset(id: string, name: string): HDASummary {
    return {
        id,
        name,
        history_content_type: "dataset",
        deleted: false,
        visible: true,
        state: "ok",
        extension: "txt",
        create_time: "2024-01-01T00:00:00",
        update_time: "2024-01-01T00:00:00",
        history_id: "history-1",
        hid: 1,
        type_id: "dataset",
        type: "file",
        tags: [],
        model_class: "HistoryDatasetAssociation",
        genome_build: null,
        purged: false,
    } as unknown as HDASummary;
}

async function mountCreator(initialElements: HDASummary[]) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);

    const wrapper = mount(PairedOrUnpairedListCollectionCreator as object, {
        propsData: {
            historyId: "history-1",
            initialElements,
            collectionType: "list:paired",
            mode: "modal",
        },
        localVue,
        pinia,
        stubs: {
            DefaultBox: true,
        },
    });

    await flushPromises();
    return wrapper;
}

/** Row ids as rendered by (our stub of) AG Grid -- this is the same identity contract
 *  (`RowT.id`, read by AG Grid's real `getRowId`) that the namespacing fix targets. */
function gridRowIds(wrapper: ReturnType<typeof mount>): string[] {
    return wrapper.findAll(".grid-row").wrappers.map((row) => row.attributes("data-row-id") ?? "");
}

describe("PairedOrUnpairedListCollectionCreator", () => {
    it("auto-pairs two elements whose names match a common filter (illumina _1/_2) on mount", async () => {
        const a = buildFakeDataset("a", "sample_1");
        const b = buildFakeDataset("b", "sample_2");

        const wrapper = await mountCreator([a, b]);

        expect(gridRowIds(wrapper)).toEqual(["pair:a"]);
    });

    it("gives a paired row and its later split-survivor row different AG Grid row ids", async () => {
        const a = buildFakeDataset("a", "sample_1");
        const b = buildFakeDataset("b", "sample_2");

        const wrapper = await mountCreator([a, b]);

        const [pairRowId] = gridRowIds(wrapper);
        expect(pairRowId).toBe("pair:a");

        // b deleted from history: pair splits, a survives as its own unpaired row
        await wrapper.setProps({ initialElements: [a] });
        await flushPromises();

        const [survivorRowId] = gridRowIds(wrapper);
        expect(survivorRowId).toBe("single:a");
        expect(survivorRowId).not.toBe(pairRowId);
    });

    it("does not resurrect a discarded survivor after history-delete splits an auto-paired pair", async () => {
        const a = buildFakeDataset("a", "sample_1");
        const b = buildFakeDataset("b", "sample_2");

        const wrapper = await mountCreator([a, b]);

        // b deleted from history: pair splits, a survives as its own unpaired row
        await wrapper.setProps({ initialElements: [a] });
        await flushPromises();
        expect(gridRowIds(wrapper)).toEqual(["single:a"]);

        // user-facing discard action: the "discard all remaining unpaired datasets" link
        await wrapper.find('[data-description="dismiss unmatched datasets"]').trigger("click");
        await flushPromises();
        expect(gridRowIds(wrapper)).toEqual([]);

        // a is still present in history (e.g. next poll tick) alongside b having come back
        // (e.g. undeleted); a must not reappear since the user explicitly discarded it, while
        // b -- never discarded, just transiently missing -- is free to come back on its own.
        await wrapper.setProps({ initialElements: [a, b] });
        await flushPromises();

        expect(gridRowIds(wrapper)).toEqual(["single:b"]);
    });
});
