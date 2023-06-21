import axios from "axios";
import MockAdapter from "axios-mock-adapter";

import { pagesProvider } from "./PageProvider";

describe("PageProvider", () => {
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    afterEach(() => {
        axiosMock.restore();
    });

    describe("fetching pages without an error", () => {
        it("should make an API call and fire callback", async () => {
            axiosMock
                .onGet("/prefix/api/pages", {
                    params: { limit: 50, offset: 0, search: "rna tutorial" },
                })
                .reply(200, [{ model_class: "Page" }], { total_matches: "1" });

            const ctx = {
                root: "/prefix/",
                perPage: 50,
                currentPage: 1,
            };
            const extras = {
                search: "rna tutorial",
            };

            let called = false;
            const callback = function () {
                called = true;
            };
            const promise = pagesProvider(ctx, callback, extras);
            await promise;
            expect(called).toBeTruthy();
        });
    });
});
