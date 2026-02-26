import { describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import { pagesProvider } from "./PageProvider";

const { server, http } = useServerMock();

describe("PageProvider", () => {
    describe("fetching pages without an error", () => {
        it("should make an API call and fire callback", async () => {
            server.use(
                http.untyped.get("/prefix/api/pages", ({ request }) => {
                    const url = new URL(request.url);
                    if (
                        url.searchParams.get("limit") === "50" &&
                        url.searchParams.get("offset") === "0" &&
                        url.searchParams.get("search") === "rna tutorial"
                    ) {
                        return HttpResponse.json([{ model_class: "Page" }], {
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
