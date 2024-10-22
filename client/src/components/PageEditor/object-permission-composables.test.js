import { set } from "vue";

import {
    initializeObjectReferences,
    initializeObjectToHistoryRefs,
    updateReferences,
} from "./object-permission-composables";

describe("object-permission-composables", () => {
    it("should initialize and update refs in a markdown document", () => {
        const refs = initializeObjectReferences();
        expect(refs.referencedJobIds.value.length).toBe(0);

        updateReferences(refs, "some content\n```galaxy\njob_metrics(job_id=THISFAKEID)\n```\nfoo bar\n");
        expect(refs.referencedJobIds.value.length).toBe(1);
        expect(refs.referencedJobIds.value[0]).toBe("THISFAKEID");
    });

    describe("initializeObjectToHistoryRefs", () => {
        function init() {
            const refs = initializeObjectReferences();
            const historyMaps = initializeObjectToHistoryRefs(refs);
            return { refs, historyMaps };
        }

        describe("historyIds computed", () => {
            it("should merge in referenced job histories once they've been cached", async () => {
                const { refs, historyMaps } = init();
                refs.referencedJobIds.value = ["THISFAKEID"];
                expect(historyMaps.historyIds.value.length).toBe(0);
                set(historyMaps.jobsToHistories.value, "THISFAKEID", "THATFAKEID");
                expect(historyMaps.historyIds.value.length).toBe(1);
                expect(historyMaps.historyIds.value[0]).toBe("THATFAKEID");
            });

            it("should merge in referenced invocation histories once they've been cached", async () => {
                const { refs, historyMaps } = init();
                refs.referencedInvocationIds.value = ["THISFAKEID"];
                expect(historyMaps.historyIds.value.length).toBe(0);
                set(historyMaps.invocationsToHistories.value, "THISFAKEID", "THATFAKEID");
                expect(historyMaps.historyIds.value.length).toBe(1);
                expect(historyMaps.historyIds.value[0]).toBe("THATFAKEID");
            });

            it("should merge in referenced collections once they've been cached", async () => {
                const { refs, historyMaps } = init();
                refs.referencedHistoryDatasetCollectionIds.value = ["THISFAKEID"];
                expect(historyMaps.historyIds.value.length).toBe(0);
                set(historyMaps.historyDatasetCollectionsToHistories.value, "THISFAKEID", "THATFAKEID");
                expect(historyMaps.historyIds.value.length).toBe(1);
                expect(historyMaps.historyIds.value[0]).toBe("THATFAKEID");
            });

            it("should merge in referenced objects across sources once they've been cached", async () => {
                const { refs, historyMaps } = init();
                refs.referencedJobIds.value = ["THISFAKEJOBID"];
                refs.referencedInvocationIds.value = ["THISFAKEINVOCATIONID"];
                refs.referencedHistoryDatasetCollectionIds.value = ["THISFAKECOLLECTIONID"];
                set(historyMaps.jobsToHistories.value, "THISFAKEJOBID", "HISTORYID1");
                set(historyMaps.invocationsToHistories.value, "THISFAKEINVOCATIONID", "HISTORYID2");
                set(historyMaps.historyDatasetCollectionsToHistories.value, "THISFAKECOLLECTIONID", "HISTORYID3");
                expect(historyMaps.historyIds.value.length).toBe(3);
                expect(historyMaps.historyIds.value).toContain("HISTORYID1");
                expect(historyMaps.historyIds.value).toContain("HISTORYID2");
                expect(historyMaps.historyIds.value).toContain("HISTORYID3");
            });

            it("should merge in referenced objects across sources once they've been cached and de-duplicate", async () => {
                const { refs, historyMaps } = init();
                refs.referencedJobIds.value = ["THISFAKEJOBID"];
                refs.referencedInvocationIds.value = ["THISFAKEINVOCATIONID"];
                refs.referencedHistoryDatasetCollectionIds.value = ["THISFAKECOLLECTIONID"];
                set(historyMaps.jobsToHistories.value, "THISFAKEJOBID", "THATFAKEID");
                set(historyMaps.invocationsToHistories.value, "THISFAKEINVOCATIONID", "THATFAKEID");
                set(historyMaps.historyDatasetCollectionsToHistories.value, "THISFAKECOLLECTIONID", "THATFAKEID");
                expect(historyMaps.historyIds.value.length).toBe(1);
                expect(historyMaps.historyIds.value[0]).toBe("THATFAKEID");
            });
        });
    });
});
