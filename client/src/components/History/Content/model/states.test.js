import { STATES, STATES_REDUCE } from "./states";

describe("States", () => {
    it("check if all reduced states exist and have a status set", async () => {
        STATES_REDUCE.forEach((datasetState) => {
            const alertState = STATES[datasetState];
            expect(alertState.status).toBeDefined();
        });
    });
});
