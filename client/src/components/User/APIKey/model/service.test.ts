import axios from "axios";
import { describe, expect, it, vi } from "vitest";

import { getAPIKey } from "./service";

vi.mock("axios");

describe("getAPIKey", () => {
    it("returns an empty list when the user has no key", async () => {
        // The page reads `result[0]`, so a user without a key needs a list, not null.
        vi.mocked(axios.get).mockResolvedValue({ status: 204, data: "" });

        const result = await getAPIKey("user-id");

        expect(result).toEqual([]);
        expect(result[0]).toBeUndefined();
    });
});
