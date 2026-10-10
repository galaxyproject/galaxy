import { getFakeDatasetSummary } from "@tests/test-data/datasets";
import { type Component, defineComponent, h, type PropType, shallowRef, watch } from "vue";

import type { HDASummary } from "@/api";
import { uploadMethodHandlers } from "@/components/Panels/Upload/test_fixtures";

import GButton from "@/components/BaseComponents/GButton.vue";

/** Requests every collection creator makes: those of the upload methods on its upload tab. */
export const collectionCreatorHandlers = { ...uploadMethodHandlers };

/** A fastqsanger dataset of sequencing reads. */
export function fastqReads(id: string, hid: number, name: string): HDASummary {
    return getFakeDatasetSummary({ id, hid, name, extension: "fastqsanger" });
}

/** A run's forward and reverse reads, named for the illumina `_1`/`_2` pairing filter. */
export const READ_PAIR = [
    fastqReads("forward-reads", 1, "SRR1553425_1"),
    fastqReads("reverse-reads", 2, "SRR1553425_2"),
] as const;

/**
 * Plays the history that feeds a collection creator its `initialElements`. Each dataset gets
 * buttons that change the history as a poll would report it: deleted, or failed. "Refresh
 * history" reports the same datasets again as new objects, and "Delete all" empties the history
 * in one update. A dataset from `history` or `arriving` that isn't in the history gets an "Add"
 * button, as an upload finishing or an undelete. Other attributes pass to the creator.
 */
export const CreatorWithHistory = defineComponent({
    name: "CreatorWithHistory",
    compatConfig: { MODE: 3 },
    inheritAttrs: false,
    props: {
        creator: { type: Object as PropType<Component>, required: true },
        history: { type: Array as PropType<HDASummary[]>, required: true },
        arriving: { type: Array as PropType<HDASummary[]>, default: () => [] },
    },
    setup(props, { attrs }) {
        const datasets = shallowRef(props.history);
        watch(
            () => props.history,
            (history) => (datasets.value = history),
        );

        function absent() {
            const present = new Set(datasets.value.map((dataset) => dataset.id));
            return [...props.history, ...props.arriving].filter((dataset) => !present.has(dataset.id));
        }

        function control(label: string, change: () => HDASummary[]) {
            return h(GButton, { size: "small", onClick: () => (datasets.value = change()) }, () => label);
        }

        return () =>
            h("div", [
                h(props.creator, { ...attrs, initialElements: datasets.value }),
                h("fieldset", { class: "mt-3" }, [
                    h("legend", "History"),
                    control("Refresh history", () => datasets.value.map((dataset) => ({ ...dataset }))),
                    control("Delete all", () => []),
                    ...datasets.value.flatMap((dataset) => [
                        control(`Delete ${dataset.name}`, () => datasets.value.filter((d) => d.id !== dataset.id)),
                        control(`Fail ${dataset.name}`, () =>
                            datasets.value.map((d) => (d.id === dataset.id ? { ...d, state: "error" as const } : d)),
                        ),
                    ]),
                    ...absent().map((dataset) => control(`Add ${dataset.name}`, () => [...datasets.value, dataset])),
                ]),
            ]);
    },
});
