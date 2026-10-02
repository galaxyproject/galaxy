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
        vi.spyOn(console, "warn").mockImplementation(() => {});
        vi.mocked(axios.get)
            .mockRejectedValueOnce(new Error("Network Error"))
            .mockResolvedValueOnce({ data: [onloadWebhook] });
        const { loadWebhooks } = await import("./webhooks");

        await expect(loadWebhooks("onload")).resolves.toEqual([]);
        await expect(loadWebhooks("onload")).resolves.toEqual([onloadWebhook]);
        expect(axios.get).toHaveBeenCalledTimes(2);
    });
});
