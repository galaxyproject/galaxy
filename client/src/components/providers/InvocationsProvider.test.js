import { describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import mockInvocationData from "@/components/Workflow/test/json/invocation.json";

import { invocationsProvider } from "./InvocationsProvider";

const { server, http } = useServerMock();

describe("invocationsProvider", () => {
    describe("fetching invocations without an error", () => {
        it("should make an API call and fire callback", async () => {
            server.use(
                http.untyped.get("/prefix/api/invocations", ({ request }) => {
                    const url = new URL(request.url);
                    if (
                        url.searchParams.get("limit") === "50" &&
                        url.searchParams.get("offset") === "0" &&
                        url.searchParams.get("include_terminal") === "false"
                    ) {
                        return HttpResponse.json([mockInvocationData], {
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
                include_terminal: false,
            };

            let called = false;
            const callback = function () {
                called = true;
            };
            const promise = invocationsProvider(ctx, callback, extras);
            await promise;
            expect(called).toBeTruthy();
        });
    });
});
