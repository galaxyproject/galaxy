import { getFakeHistorySummary } from "@tests/test-data";
import { getFakeCollectionSummary } from "@tests/test-data/collections";
import { getFakeDatasetSummary } from "@tests/test-data/datasets";

import type { HDASummary, HistoryItemSummary } from "@/api";

/** The history whose items are selected. */
export const HISTORY = getFakeHistorySummary({
    id: "history-1",
    name: "RNA-seq run",
    count: 5,
    url: "/api/histories/history-1",
});

function dataset(overrides: Partial<HDASummary>): HDASummary {
    return getFakeDatasetSummary({ history_id: HISTORY.id, extension: "fastqsanger", ...overrides });
}

export const VISIBLE_DATASET = dataset({ id: "dataset-1", hid: 1, name: "SRR1234_1.fastq" });
export const HIDDEN_DATASET = dataset({ id: "dataset-2", hid: 2, name: "SRR1234_2.fastq", visible: false });
export const DELETED_DATASET = dataset({ id: "dataset-3", hid: 3, name: "trimmed_1.fastq", deleted: true });
export const PURGED_DATASET = dataset({
    id: "dataset-4",
    hid: 4,
    name: "trimmed_2.fastq",
    deleted: true,
    purged: true,
});
/** Collections carry no `purged` flag. */
export const READS_COLLECTION = getFakeCollectionSummary({
    id: "collection-1",
    hid: 5,
    history_id: HISTORY.id,
    name: "Paired reads",
});

/** Selected items as the history panel keeps them, keyed by content type and id. */
export function selectionOf(...items: HistoryItemSummary[]): Map<string, HistoryItemSummary> {
    return new Map(items.map((item) => [`${item.history_content_type}-${item.id}`, item]));
}

/** `count` visible datasets, for a selection larger than the defaults. */
export function visibleDatasets(count: number): HDASummary[] {
    return Array.from({ length: count }, (_, index) =>
        dataset({ id: `dataset-${index + 10}`, hid: index + 10, name: `sample_${index + 1}.fastq` }),
    );
}
