import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { h, ref } from "vue";

import type { HDASummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { Toast } from "@/composables/toast";
import { usePairingDatasetTargetsStore } from "@/stores/collectionBuilderItemsStore";

import PairedOrUnpairedListCollectionCreator from "./PairedOrUnpairedListCollectionCreator.vue";

vi.mock("@/composables/toast");

const toastError = vi.mocked(Toast.error);
const toastWarning = vi.mocked(Toast.warning);

const localVue = getLocalVue(true);

vi.mock("@/composables/useAgGrid", () => ({
    useAgGrid: () => ({
        gridApi: ref(null),
        AgGridVue: {
            name: "AgGridVue",
            props: ["rowData"],
            render() {
                const self = this as unknown as { rowData: { id: string }[] };
                return h(
                    "div",
                    {},
                    (self.rowData || []).map((row) => h("div", { class: "grid-row", "data-row-id": row.id }, [])),
                );
            },
        },
        onGridReady: () => {},
        theme: "ag-theme-alpine",
    }),
}));

const { server, http } = useServerMock();
beforeEach(() => {
    vi.clearAllMocks();
    server.use(
        http.get("/api/configuration", ({ response }) => response(200).json({})),
        http.get("/api/genomes", ({ response }) => response(200).json([])),
    );
});

function buildFakeDataset(id: string, name: string, hid = 1): HDASummary {
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
        hid,
        type_id: "dataset",
        type: "file",
        tags: [],
        model_class: "HistoryDatasetAssociation",
        genome_build: null,
        purged: false,
    } as unknown as HDASummary;
}

async function mountCreator(initialElements: HDASummary[]) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);

    const wrapper = mount(PairedOrUnpairedListCollectionCreator, {
        props: {
            historyId: "history-1",
            initialElements,
            collectionType: "list:paired",
            mode: "modal",
        },
        global: withPlugins(localVue, pinia),
    });

    await flushPromises();
    return wrapper;
}

/** Row ids as our AG Grid stub renders them - the `RowT.id` contract the namespacing fix targets. */
function gridRowIds(wrapper: ReturnType<typeof mount>): string[] {
    return wrapper.findAll(".grid-row").map((row) => row.attributes("data-row-id") ?? "");
}

describe("PairedOrUnpairedListCollectionCreator", () => {
    it("auto-pairs two elements whose names match a common filter (illumina _1/_2) on mount", async () => {
        const a = buildFakeDataset("a", "sample_1");
        const b = buildFakeDataset("b", "sample_2");

        const wrapper = await mountCreator([a, b]);

        expect(gridRowIds(wrapper)).toEqual(["pair:a"]);
    });

    it("auto-pairs mates that arrive in separate history updates", async () => {
        const a = buildFakeDataset("a", "hello world.1.fastq");
        const b = buildFakeDataset("b", "hello world.2.fastq");

        const wrapper = await mountCreator([]);
        await wrapper.setProps({ initialElements: [a] });
        await flushPromises();
        expect(gridRowIds(wrapper)).toEqual(["single:a"]);

        await wrapper.setProps({ initialElements: [a, b] });
        await flushPromises();

        expect(gridRowIds(wrapper)).toEqual(["pair:a"]);
    });

    it("does not re-pair mates the user unpaired when another element arrives", async () => {
        const a = buildFakeDataset("a", "sample_1");
        const b = buildFakeDataset("b", "sample_2");
        const c = buildFakeDataset("c", "other_1");

        const wrapper = await mountCreator([a, b]);
        expect(gridRowIds(wrapper)).toEqual(["pair:a"]);

        const { context } = wrapper.findComponent({ name: "AgGridVue" }).vm.$attrs as unknown as {
            context: { onUnpair: (pair: { forward: HDASummary; reverse: HDASummary; name: string }) => void };
        };
        context.onUnpair({ forward: a, reverse: b, name: "sample" });
        await flushPromises();
        expect(gridRowIds(wrapper)).toEqual(["single:a", "single:b"]);

        await wrapper.setProps({ initialElements: [a, b, c] });
        await flushPromises();

        expect(gridRowIds(wrapper)).toEqual(["single:a", "single:b", "single:c"]);
    });

    it.each(["auto-paired", "removed"])(
        "allows click-pairing after the selected dataset is %s by a history update",
        async (change) => {
            const a = buildFakeDataset("a", "sample_1");
            const b = buildFakeDataset("b", "sample_2");
            const c = buildFakeDataset("c", "unmatched-c");
            const d = buildFakeDataset("d", "unmatched-d");
            const wrapper = await mountCreator([a, c, d]);
            const pairingTargetsStore = usePairingDatasetTargetsStore();
            const { context } = wrapper.findComponent({ name: "AgGridVue" }).vm.$attrs as unknown as {
                context: { onUnpairedClick: (value: { unpaired: HDASummary }) => void };
            };

            context.onUnpairedClick({ unpaired: a });
            expect(pairingTargetsStore.unpairedTarget).toBe("a");

            await wrapper.setProps({ initialElements: change === "auto-paired" ? [a, b, c, d] : [c, d] });
            await flushPromises();
            expect(gridRowIds(wrapper)).toEqual(
                change === "auto-paired" ? ["pair:a", "single:c", "single:d"] : ["single:c", "single:d"],
            );
            expect(pairingTargetsStore.unpairedTarget).toBeNull();

            context.onUnpairedClick({ unpaired: c });
            expect(pairingTargetsStore.unpairedTarget).toBe("c");
            context.onUnpairedClick({ unpaired: d });
            await flushPromises();

            expect(gridRowIds(wrapper)).toEqual(change === "auto-paired" ? ["pair:a", "pair:c"] : ["pair:c"]);
            expect(pairingTargetsStore.unpairedTarget).toBeNull();
        },
    );

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

    it("warns rather than errors for the vanished half of a pair that could never have been one", async () => {
        const a = buildFakeDataset("a", "sample_1", 1);
        const b = buildFakeDataset("b", "sample_2", 2);

        // list:paired - an unpaired survivor never reaches the collection, so it warns rather
        // than claiming the vanished half was "removed from the collection"
        const wrapper = await mountCreator([a, b]);
        await wrapper.setProps({ initialElements: [a] });
        await flushPromises();

        expect(toastError).not.toHaveBeenCalled();
        expect(toastWarning).toHaveBeenCalledTimes(1);
        expect(toastWarning).toHaveBeenCalledWith(
            "2: sample_2 is no longer available and was removed from the pairing list",
            "Dataset unavailable",
        );
    });

    it("describes a wholly vanished pair in one notification rather than one per side", async () => {
        const a = buildFakeDataset("a", "sample_1", 1);
        const b = buildFakeDataset("b", "sample_2", 2);

        const wrapper = await mountCreator([a, b]);
        await wrapper.setProps({ initialElements: [] });
        await flushPromises();

        expect(toastError).toHaveBeenCalledTimes(1);
        expect(toastError).toHaveBeenCalledWith(
            "1: sample_1, 2: sample_2 has been removed from the collection",
            "Invalid element",
        );
    });

    it("does not resurrect a discarded survivor after history-delete splits an auto-paired pair", async () => {
        const a = buildFakeDataset("a", "sample_1");
        const b = buildFakeDataset("b", "sample_2");

        const wrapper = await mountCreator([a, b]);

        // b deleted from history: pair splits, a survives as its own unpaired row
        await wrapper.setProps({ initialElements: [a] });
        await flushPromises();
        expect(gridRowIds(wrapper)).toEqual(["single:a"]);

        await wrapper.find('[data-description="dismiss unmatched datasets"]').trigger("click");
        await flushPromises();
        expect(gridRowIds(wrapper)).toEqual([]);

        // b comes back (undeleted) and a is still in the history: a stays gone because the user
        // discarded it, b returns because it was only transiently missing
        await wrapper.setProps({ initialElements: [a, b] });
        await flushPromises();

        expect(gridRowIds(wrapper)).toEqual(["single:b"]);
    });
});
