import { describe, expect, it } from "vitest";

import {
    initializeObjectReferences,
    initializeObjectToHistoryRefs,
    updateReferences,
} from "./object-permission-composables";

function createHistoryReferences() {
    const refs = initializeObjectReferences();
    return { refs, historyMaps: initializeObjectToHistoryRefs(refs) };
}

describe("object-permission-composables", () => {
    it("extracts job references from a Galaxy markdown block", () => {
        const refs = initializeObjectReferences();
        expect(refs.referencedJobIds.value).toEqual([]);

        updateReferences(refs, "some content\n```galaxy\njob_metrics(job_id=THISFAKEID)\n```\nfoo bar\n");

        expect(refs.referencedJobIds.value).toEqual(["THISFAKEID"]);
    });

    describe("referenced history IDs", () => {
        it.each([
            ["jobs", "referencedJobIds", "jobsToHistories"],
            ["invocations", "referencedInvocationIds", "invocationsToHistories"],
            ["collections", "referencedHistoryDatasetCollectionIds", "historyDatasetCollectionsToHistories"],
        ])("includes histories referenced by %s once their mapping is cached", (_source, referenceKey, mappingKey) => {
            const { refs, historyMaps } = createHistoryReferences();
            refs[referenceKey].value = ["THISFAKEID"];
            expect(historyMaps.historyIds.value).toEqual([]);

            historyMaps[mappingKey].value["THISFAKEID"] = "THATFAKEID";

            expect(historyMaps.historyIds.value).toEqual(["THATFAKEID"]);
        });

        it("merges cached histories from jobs, invocations, and collections", () => {
            const { refs, historyMaps } = createHistoryReferences();
            refs.referencedJobIds.value = ["THISFAKEJOBID"];
            refs.referencedInvocationIds.value = ["THISFAKEINVOCATIONID"];
            refs.referencedHistoryDatasetCollectionIds.value = ["THISFAKECOLLECTIONID"];
            historyMaps.jobsToHistories.value.THISFAKEJOBID = "HISTORYID1";
            historyMaps.invocationsToHistories.value.THISFAKEINVOCATIONID = "HISTORYID2";
            historyMaps.historyDatasetCollectionsToHistories.value.THISFAKECOLLECTIONID = "HISTORYID3";

            expect(historyMaps.historyIds.value).toHaveLength(3);
            expect(historyMaps.historyIds.value).toEqual(
                expect.arrayContaining(["HISTORYID1", "HISTORYID2", "HISTORYID3"]),
            );
        });

        it("de-duplicates a history referenced by all three sources", () => {
            const { refs, historyMaps } = createHistoryReferences();
            refs.referencedJobIds.value = ["THISFAKEJOBID"];
            refs.referencedInvocationIds.value = ["THISFAKEINVOCATIONID"];
            refs.referencedHistoryDatasetCollectionIds.value = ["THISFAKECOLLECTIONID"];
            historyMaps.jobsToHistories.value.THISFAKEJOBID = "THATFAKEID";
            historyMaps.invocationsToHistories.value.THISFAKEINVOCATIONID = "THATFAKEID";
            historyMaps.historyDatasetCollectionsToHistories.value.THISFAKECOLLECTIONID = "THATFAKEID";

            expect(historyMaps.historyIds.value).toEqual(["THATFAKEID"]);
        });
    });
});
