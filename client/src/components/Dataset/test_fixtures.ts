import { getFakeHistorySummary } from "@tests/test-data";
import { getFakeCollectionSummary } from "@tests/test-data/collections";
import { getFakeDatasetSummary } from "@tests/test-data/datasets";

import type { HDASummary, HDCASummary, HistorySummary } from "@/api";

function history(id: string, name: string, data: Partial<HistorySummary> = {}) {
    return getFakeHistorySummary({ id, name, url: `/api/histories/${id}`, ...data });
}

export const RNA_SEQ = history("a3f8c2e17b90d465", "RNA-seq run");
export const VARIANT_CALLING = history("5d2e9b4a71c03f86", "Variant calling");
export const EMPTY_HISTORY = history("e81b6c0d4f2a9375", "Unnamed history");
/** Deleted histories aren't in the history list, though one can still be current. */
export const DELETED_HISTORY = history("97c4a1f8e2b5d063", "Old mapping run", { deleted: true });

function dataset(historyId: string, id: string, hid: number, name: string): HDASummary {
    return getFakeDatasetSummary({ id, hid, name, history_id: historyId, extension: "fastqsanger" });
}

export const FORWARD_READS = dataset(RNA_SEQ.id, "b72e0f5a9c3d1648", 1, "SRR1553425_1.fastq");
export const REVERSE_READS = dataset(RNA_SEQ.id, "c18d4a6e2f9b0753", 2, "SRR1553425_2.fastq");
export const PAIRED_READS: HDCASummary = getFakeCollectionSummary({
    id: "d905f3b1e7a2c846",
    hid: 3,
    name: "SRR1553425",
    history_id: RNA_SEQ.id,
    collection_type: "paired",
    element_count: 2,
    elements_datatypes: ["fastqsanger"],
});

/** Each history's contents, by history id. */
export const HISTORY_CONTENTS: Record<string, (HDASummary | HDCASummary)[]> = {
    [RNA_SEQ.id]: [FORWARD_READS, REVERSE_READS, PAIRED_READS],
    [VARIANT_CALLING.id]: [dataset(VARIANT_CALLING.id, "f4a7e2c9b0d13586", 1, "mutant_R1.fastq")],
    [EMPTY_HISTORY.id]: [],
    [DELETED_HISTORY.id]: [dataset(DELETED_HISTORY.id, "0e6b3d8f5a1c2947", 1, "SRR1553425.bam")],
};
