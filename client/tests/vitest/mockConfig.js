import { vi } from "vitest";

import { useConfig } from "@/composables/config";

vi.mock("@/composables/config");

export function setupMockConfig(configValues, isConfigLoaded = true) {
    return useConfig.mockReturnValue({
        config: { value: configValues },
        isConfigLoaded: isConfigLoaded,
    });
}
