import { describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import { storedWorkflowsProvider } from "./StoredWorkflowsProvider";

const { server, http } = useServerMock();

describe("storedWorkflowsProvider", () => {
    describe("fetching workflows without an error", () => {
        it("should make an API call and fire callback", async () => {
            server.use(
                http.untyped.get("/prefix/api/workflows", ({ request }) => {
                    const url = new URL(request.url);
                    if (
                        url.searchParams.get("limit") === "50" &&
                        url.searchParams.get("offset") === "0" &&
                        url.searchParams.get("skip_step_counts") === "true" &&
                        url.searchParams.get("search") === "rna"
                    ) {
                        return HttpResponse.json([{ model_class: "StoredWorkflow" }], {
                            headers: { total_matches: "1" },
                        });
                    }
                    return HttpResponse.json([]);
                }),
            );

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
