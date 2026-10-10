import { composeStories } from "@storybook/vue3-vite";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import type { VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { h, ref } from "vue";

import type { HDASummary } from "@/api";
import { Toast } from "@/composables/toast";
import { usePairingDatasetTargetsStore } from "@/stores/collectionBuilderItemsStore";

import * as PairedOrUnpairedListCollectionCreatorStories from "./PairedOrUnpairedListCollectionCreator.stories";
import { changeHistory } from "./test-utils";

vi.mock("@/composables/toast");

const toastError = vi.mocked(Toast.error);
const toastWarning = vi.mocked(Toast.warning);

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

const stories = composeStories(PairedOrUnpairedListCollectionCreatorStories);
const mountStory = useStoryMount();

const [FORWARD, REVERSE] = stories.ReadPairInHistory.args.history as [HDASummary, HDASummary];
const [NEXT_RUN_FORWARD] = stories.ReadPairInHistory.args.arriving as [HDASummary];
const [FORWARD_UPLOAD, REVERSE_UPLOAD] = stories.ReadPairStillUploading.args.arriving as [HDASummary, HDASummary];
const [AWAITING_FORWARD, CONTROL_FORWARD, CONTROL_REVERSE] = stories.ForwardReadsAwaitingMate.args.history as [
    HDASummary,
    HDASummary,
    HDASummary,
];
const [AWAITED_REVERSE] = stories.ForwardReadsAwaitingMate.args.arriving as [HDASummary];

beforeEach(() => {
    vi.clearAllMocks();
});

async function mountCreator(story: StoryOf<typeof stories>) {
    const wrapper = mountStory(story);
    await flushPromises();
    return wrapper;
}

/** Row ids as our AG Grid stub renders them - the `RowT.id` contract the namespacing fix targets. */
function gridRowIds(wrapper: VueWrapper): string[] {
    return wrapper.findAll(".grid-row").map((row) => row.attributes("data-row-id") ?? "");
}

const pairRow = (forward: HDASummary) => `pair:${forward.id}`;
const singleRow = (dataset: HDASummary) => `single:${dataset.id}`;

/** The callbacks the creator hands its grid's cell renderers. */
function gridContext(wrapper: VueWrapper) {
    return wrapper.findComponent({ name: "AgGridVue" }).vm.$attrs.context as {
        onUnpair: (pair: { forward: HDASummary; reverse: HDASummary; name: string }) => void;
        onUnpairedClick: (value: { unpaired: HDASummary }) => void;
    };
}

describe("PairedOrUnpairedListCollectionCreator", () => {
    it("auto-pairs two elements whose names match a common filter (illumina _1/_2) on mount", async () => {
        const wrapper = await mountCreator(stories.ReadPairInHistory);

        expect(gridRowIds(wrapper)).toEqual([pairRow(FORWARD)]);
    });

    it("auto-pairs mates that arrive in separate history updates", async () => {
        const wrapper = await mountCreator(stories.ReadPairStillUploading);
        await changeHistory(wrapper, `Add ${FORWARD_UPLOAD.name}`);
        expect(gridRowIds(wrapper)).toEqual([singleRow(FORWARD_UPLOAD)]);

        await changeHistory(wrapper, `Add ${REVERSE_UPLOAD.name}`);

        expect(gridRowIds(wrapper)).toEqual([pairRow(FORWARD_UPLOAD)]);
    });

    it("does not re-pair mates the user unpaired when another element arrives", async () => {
        const wrapper = await mountCreator(stories.ReadPairInHistory);
        expect(gridRowIds(wrapper)).toEqual([pairRow(FORWARD)]);

        gridContext(wrapper).onUnpair({ forward: FORWARD, reverse: REVERSE, name: "SRR1553425" });
        await flushPromises();
        expect(gridRowIds(wrapper)).toEqual([singleRow(FORWARD), singleRow(REVERSE)]);

        await changeHistory(wrapper, `Add ${NEXT_RUN_FORWARD.name}`);

        expect(gridRowIds(wrapper)).toEqual([singleRow(FORWARD), singleRow(REVERSE), singleRow(NEXT_RUN_FORWARD)]);
    });

    it.each([
        {
            change: "auto-paired",
            historyControl: `Add ${AWAITED_REVERSE.name}`,
            rowsAfterChange: [pairRow(AWAITING_FORWARD), singleRow(CONTROL_FORWARD), singleRow(CONTROL_REVERSE)],
            rowsAfterClickPairing: [pairRow(AWAITING_FORWARD), pairRow(CONTROL_FORWARD)],
        },
        {
            change: "removed",
            historyControl: `Delete ${AWAITING_FORWARD.name}`,
            rowsAfterChange: [singleRow(CONTROL_FORWARD), singleRow(CONTROL_REVERSE)],
            rowsAfterClickPairing: [pairRow(CONTROL_FORWARD)],
        },
    ])(
        "allows click-pairing after the selected dataset is $change by a history update",
        async ({ historyControl, rowsAfterChange, rowsAfterClickPairing }) => {
            const wrapper = await mountCreator(stories.ForwardReadsAwaitingMate);
            const pairingTargetsStore = usePairingDatasetTargetsStore();
            const { onUnpairedClick } = gridContext(wrapper);

            onUnpairedClick({ unpaired: AWAITING_FORWARD });
            expect(pairingTargetsStore.unpairedTarget).toBe(AWAITING_FORWARD.id);

            await changeHistory(wrapper, historyControl);
            expect(gridRowIds(wrapper)).toEqual(rowsAfterChange);
            expect(pairingTargetsStore.unpairedTarget).toBeNull();

            onUnpairedClick({ unpaired: CONTROL_FORWARD });
            expect(pairingTargetsStore.unpairedTarget).toBe(CONTROL_FORWARD.id);
            onUnpairedClick({ unpaired: CONTROL_REVERSE });
            await flushPromises();

            expect(gridRowIds(wrapper)).toEqual(rowsAfterClickPairing);
            expect(pairingTargetsStore.unpairedTarget).toBeNull();
        },
    );

    it("gives a paired row and its later split-survivor row different AG Grid row ids", async () => {
        const wrapper = await mountCreator(stories.ReadPairInHistory);

        const [pairRowId] = gridRowIds(wrapper);
        expect(pairRowId).toBe(pairRow(FORWARD));

        // reverse deleted from history: pair splits, forward survives as its own unpaired row
        await changeHistory(wrapper, `Delete ${REVERSE.name}`);

        const [survivorRowId] = gridRowIds(wrapper);
        expect(survivorRowId).toBe(singleRow(FORWARD));
        expect(survivorRowId).not.toBe(pairRowId);
    });

    it("warns rather than errors for the vanished half of a pair that could never have been one", async () => {
        // list:paired - an unpaired survivor never reaches the collection, so it warns rather
        // than claiming the vanished half was "removed from the collection"
        const wrapper = await mountCreator(stories.ReadPairInHistory);
        await changeHistory(wrapper, `Delete ${REVERSE.name}`);

        expect(toastError).not.toHaveBeenCalled();
        expect(toastWarning).toHaveBeenCalledTimes(1);
        expect(toastWarning).toHaveBeenCalledWith(
            "2: SRR1553425_2 is no longer available and was removed from the pairing list",
            "Dataset unavailable",
        );
    });

    it("describes a wholly vanished pair in one notification rather than one per side", async () => {
        const wrapper = await mountCreator(stories.ReadPairInHistory);
        // both sides leave in the same history update
        await changeHistory(wrapper, "Delete all");

        expect(toastError).toHaveBeenCalledTimes(1);
        expect(toastError).toHaveBeenCalledWith(
            "1: SRR1553425_1, 2: SRR1553425_2 has been removed from the collection",
            "Invalid element",
        );
    });

    it("does not resurrect a discarded survivor after history-delete splits an auto-paired pair", async () => {
        const wrapper = await mountCreator(stories.ReadPairInHistory);

        // reverse deleted from history: pair splits, forward survives as its own unpaired row
        await changeHistory(wrapper, `Delete ${REVERSE.name}`);
        expect(gridRowIds(wrapper)).toEqual([singleRow(FORWARD)]);

        await wrapper.find('[data-description="dismiss unmatched datasets"]').trigger("click");
        await flushPromises();
        expect(gridRowIds(wrapper)).toEqual([]);

        // reverse comes back (undeleted) and forward is still in the history: forward stays gone
        // because the user discarded it, reverse returns because it was only transiently missing
        await changeHistory(wrapper, `Add ${REVERSE.name}`);

        expect(gridRowIds(wrapper)).toEqual([singleRow(REVERSE)]);
    });
});
