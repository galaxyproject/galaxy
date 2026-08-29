import axios from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { searchHistoryContents } from "./services";

vi.mock("axios", () => ({
    default: {
        get: vi.fn(),
    },
}));

vi.mock("@/onload/loadConfig", () => ({
    getAppRoot: () => "/",
}));

describe("workflow run services", () => {
    beforeEach(() => {
        vi.mocked(axios.get).mockReset();
        vi.mocked(axios.get).mockResolvedValue({ data: [] });
    });

    it("preserves a workflow input tag when paging history contents", async () => {
        await searchHistoryContents("history-id", {
            type: "dataset",
            tag: "genomescope_model",
            offset: 50,
            limit: 50,
        });

        const requestUrl = new URL(vi.mocked(axios.get).mock.calls[0][0], "http://localhost");
        expect(requestUrl.searchParams.getAll("q")).toContain("tag-eq");
        expect(requestUrl.searchParams.getAll("qv")).toContain("genomescope_model");
        expect(requestUrl.searchParams.get("offset")).toBe("50");
    });
});
