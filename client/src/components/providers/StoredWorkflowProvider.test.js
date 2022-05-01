import axios from "axios";
import MockAdapter from "axios-mock-adapter";

import { storedWorkflowsProvider } from "./StoredWorkflowsProvider";

describe("storedWorkflowsProvider", () => {
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    afterEach(() => {
        axiosMock.restore();
    });

    describe("fetching workflows without an error", () => {
        it("should make an API call and fire callback", async () => {
            axiosMock
                .onGet("/prefix/api/workflows", {
                    params: { limit: 50, offset: 0, skip_step_counts: true, search: "rna" },
                })
                .reply(200, [{ model_class: "StoredWorkflow" }], { total_matches: "1" });

            const ctx = {
                root: "/prefix/",
                perPage: 50,
                currentPage: 1,
            };
            const extras = {
                skip_step_counts: true,
                search: "rna",
            };

            let called = false;
            const callback = function () {
                called = true;
            };
            const promise = storedWorkflowsProvider(ctx, callback, extras);
            await promise;
            expect(called).toBeTruthy();
        });
    });
});
