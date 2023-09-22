import { STATES, HIERARCHICAL_COLLECTION_JOB_STATES } from "./states";

describe("States", () => {
    it("check if all reduced states exist and have a status set", async () => {
        HIERARCHICAL_COLLECTION_JOB_STATES.forEach((jobState) => {
            const alertState = STATES[jobState];
            expect(alertState.status).toBeDefined();
        });
    });
});
