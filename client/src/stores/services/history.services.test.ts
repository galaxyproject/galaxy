import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import { getHistoryList } from "./history.services";

const { server, http } = useServerMock();

function mockHistoryList() {
    const requests: URLSearchParams[] = [];

    server.use(
        http.get("/api/histories", ({ request, response }) => {
            requests.push(new URL(request.url).searchParams);
            return response(200).json([]);
        }),
    );

    return requests;
}

describe("getHistoryList", () => {
    it("restricts the listing to histories owned by the current user", async () => {
        const requests = mockHistoryList();

        await getHistoryList();

        expect(requests).toHaveLength(1);
        const params = requests[0]!;
        expect(params.get("show_own")).toBe("true");
        expect(params.get("show_published")).toBe("false");
        expect(params.get("show_shared")).toBe("false");
    });

    it("keeps the ownership flags when paginating and filtering", async () => {
        const requests = mockHistoryList();

        await getHistoryList(20, 25, "q=name-contains&qv=zebrafish");

        expect(requests).toHaveLength(1);
        const params = requests[0]!;
        expect(params.get("show_own")).toBe("true");
        expect(params.get("show_published")).toBe("false");
        expect(params.get("show_shared")).toBe("false");
        expect(params.get("offset")).toBe("20");
        expect(params.get("limit")).toBe("25");
        expect(params.get("qv")).toBe("zebrafish");
    });
});
