import { describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import mockInvocationData from "@/components/Workflow/test/json/invocation.json";

import { invocationsProvider } from "./InvocationsProvider";

const { server, http } = useServerMock();

describe("invocationsProvider", () => {
    it("fetches the first page under the configured root and passes the response to its callback", async () => {
        server.use(
            http.untyped.get("/prefix/api/invocations", ({ request }) => {
                const url = new URL(request.url);
                expect(Object.fromEntries(url.searchParams)).toEqual({
                    limit: "50",
                    offset: "0",
                    include_terminal: "false",
                });
                return HttpResponse.json([mockInvocationData], { headers: { total_matches: "1" } });
            }),
        );
        const callback = vi.fn();

        const items = await invocationsProvider({ root: "/prefix/", perPage: 50, currentPage: 1 }, callback, {
            include_terminal: false,
        });

        expect(items).toEqual([mockInvocationData]);
        expect(callback).toHaveBeenCalledTimes(1);
        expect(callback.mock.calls[0][0].data).toEqual([mockInvocationData]);
        expect(callback.mock.calls[0][0].headers.total_matches).toBe("1");
    });
});
