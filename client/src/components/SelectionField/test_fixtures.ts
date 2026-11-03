import { getFakeHistorySummary } from "@tests/test-data";
import { getFakeDatasetSummary } from "@tests/test-data/datasets";

import type { HDASummary } from "@/api";

const CURRENT_HISTORY_ID = "a7e3b9c1d5f20864";

export const CURRENT_HISTORY = getFakeHistorySummary({
    id: CURRENT_HISTORY_ID,
    name: "RNA-seq run",
    url: `/api/histories/${CURRENT_HISTORY_ID}`,
});

function historyDataset(id: string, hid: number, name: string, extension: string): HDASummary & { name: string } {
    return { ...getFakeDatasetSummary({ id, hid, extension, history_id: CURRENT_HISTORY.id }), name };
}

/** The current history's datasets, oldest first: a run's reads and the counts made from them. */
export const HISTORY_DATASETS = [
    historyDataset("forward-reads", 1, "SRR1553425_1.fastq", "fastqsanger"),
    historyDataset("reverse-reads", 2, "SRR1553425_2.fastq", "fastqsanger"),
    historyDataset("gene-counts", 3, "featureCounts on data 1 and data 2", "tabular"),
] as const;
