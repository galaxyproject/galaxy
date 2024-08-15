import axios from "axios";
import MockAdapter from "axios-mock-adapter";

import { jobsProvider } from "./JobProvider";

describe("JobProvider", () => {
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    afterEach(() => {
        axiosMock.restore();
    });

    describe("fetching jobs without an error", () => {
        it("should make an API call and fire callback", async () => {
            axiosMock
                .onGet("/prefixj/api/jobs", {
                    params: { limit: 50, offset: 0, search: "tool_id:'cat1'" },
                })
                .reply(200, [{ model_class: "Job" }], { total_matches: "1" });

            const ctx = {
                root: "/prefixj/",
                perPage: 50,
                currentPage: 1,
            };
            const extras = {
                search: "tool_id:'cat1'",
            };

            let called = false;
            const callback = function () {
                called = true;
            };
            const promise = jobsProvider(ctx, callback, extras);
            await promise;
            expect(called).toBeTruthy();
        });
    });
});
