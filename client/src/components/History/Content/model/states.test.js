import { describe, expect, it } from "vitest";

import { HIERARCHICAL_COLLECTION_DATASET_STATES, HIERARCHICAL_COLLECTION_JOB_STATES, STATES } from "./states";

describe("STATES", () => {
    it.each(HIERARCHICAL_COLLECTION_JOB_STATES)("gives collection job state '%s' a status", (jobState) => {
        expect(STATES).toHaveProperty([jobState, "status"], expect.anything());
    });

    it.each(HIERARCHICAL_COLLECTION_DATASET_STATES)("gives collection dataset state '%s' a status", (datasetState) => {
        expect(STATES).toHaveProperty([datasetState, "status"], expect.anything());
    });
});
