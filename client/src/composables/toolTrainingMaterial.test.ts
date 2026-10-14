import flushPromises from "flush-promises";
import { afterEach, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useToolTrainingMaterial } from "./toolTrainingMaterial";

vi.mock("./config", () => ({
    useConfig: () => ({
        config: ref({
            tool_training_recommendations: true,
            tool_training_recommendations_api_url: "https://training.example.org/api/top-tools.json",
        }),
        isConfigLoaded: ref(true),
    }),
}));

afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

it("tolerates a training material request that fails to reach the server", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});

    useToolTrainingMaterial("cat1", "Concatenate", "1.0.0");
    await flushPromises();

    expect(warn).toHaveBeenCalled();
});
