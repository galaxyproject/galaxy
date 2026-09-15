import axios from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getHistoryList } from "./history.services";

vi.mock("axios", () => ({
    default: {
        get: vi.fn(),
    },
}));

const mockedGet = vi.mocked(axios.get);

/** The url the last `axios.get` call was made with, parsed as query params. */
function lastRequestParams() {
    const url = mockedGet.mock.calls.at(-1)?.[0] as string;
    return new URLSearchParams(url.slice(url.indexOf("?") + 1));
}

describe("getHistoryList", () => {
    beforeEach(() => {
        mockedGet.mockReset();
        mockedGet.mockResolvedValue({ status: 200, data: [] } as any);
    });

    it("restricts the listing to histories owned by the current user", async () => {
        await getHistoryList();

        const params = lastRequestParams();
        expect(params.get("show_own")).toBe("true");
        expect(params.get("show_published")).toBe("false");
        expect(params.get("show_shared")).toBe("false");
    });

    it("keeps the ownership flags when paginating and filtering", async () => {
        await getHistoryList(20, 25, "q=name-contains&qv=zebrafish");

        const params = lastRequestParams();
        expect(params.get("show_own")).toBe("true");
        expect(params.get("show_published")).toBe("false");
        expect(params.get("show_shared")).toBe("false");
        expect(params.get("offset")).toBe("20");
        expect(params.get("limit")).toBe("25");
        expect(params.get("qv")).toBe("zebrafish");
    });
});
