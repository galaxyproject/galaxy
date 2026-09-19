import { describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import { jobsProvider } from "./JobProvider";

const { server, http } = useServerMock();

describe("JobProvider", () => {
    describe("fetching jobs without an error", () => {
        it("should make an API call and fire callback", async () => {
            server.use(
                http.untyped.get("/prefixj/api/jobs", ({ request }) => {
                    const url = new URL(request.url);
                    if (
                        url.searchParams.get("limit") === "50" &&
                        url.searchParams.get("offset") === "0" &&
                        url.searchParams.get("search") === "tool_id:'cat1'"
                    ) {
                        return HttpResponse.json([{ model_class: "Job" }], {
                            headers: { total_matches: "1" },
                        });
                    }
                    return HttpResponse.json([]);
                }),
            );

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
