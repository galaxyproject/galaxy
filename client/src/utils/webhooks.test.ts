import axios from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("axios");
vi.mock("@/onload/loadConfig", () => ({ getAppRoot: () => "/" }));

const onloadWebhook = { id: "onload_hook", type: ["onload"], activate: true };

describe("loadWebhooks", () => {
    beforeEach(() => {
        vi.resetModules();
        vi.mocked(axios.get).mockReset();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("returns no webhooks when the request fails and retries on the next call", async () => {
        const warning = vi.spyOn(console, "warn").mockImplementation(() => {});
        const requestError = new Error("Network Error");
        vi.mocked(axios.get)
            .mockRejectedValueOnce(requestError)
            .mockResolvedValueOnce({ data: [onloadWebhook] });
        const { loadWebhooks } = await import("./webhooks");

        await expect(loadWebhooks("onload")).resolves.toEqual([]);
        expect(warning).toHaveBeenCalledWith("Failed to load webhooks", requestError);
        await expect(loadWebhooks("onload")).resolves.toEqual([onloadWebhook]);
        expect(axios.get).toHaveBeenCalledTimes(2);
    });
});
