import { describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import { pagesProvider } from "./PageProvider";

const { server, http } = useServerMock();

describe("pagesProvider", () => {
    it("fetches the requested page and search under the configured root and passes the response to its callback", async () => {
        let requestParams;
        server.use(
            http.untyped.get("/prefix/api/pages", ({ request }) => {
                requestParams = Object.fromEntries(new URL(request.url).searchParams);
                return HttpResponse.json([{ model_class: "Page" }], { headers: { total_matches: "1" } });
            }),
        );
        const callback = vi.fn();

        const items = await pagesProvider({ root: "/prefix/", perPage: 50, currentPage: 1 }, callback, {
            search: "rna tutorial",
        });

        expect(requestParams).toEqual({ limit: "50", offset: "0", search: "rna tutorial" });
        expect(items).toEqual([{ model_class: "Page" }]);
        expect(callback).toHaveBeenCalledTimes(1);
        expect(callback.mock.calls[0][0].data).toEqual([{ model_class: "Page" }]);
        expect(callback.mock.calls[0][0].headers.total_matches).toBe("1");
    });
});
