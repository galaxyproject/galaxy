import { vi } from "vitest";
import { ref } from "vue";

import { useConfig } from "@/composables/config";

vi.mock("@/composables/config");

export function setupMockConfig(configValues, isConfigLoaded = true) {
    return useConfig.mockReturnValue({
        config: ref(configValues),
        isConfigLoaded: ref(isConfigLoaded),
    });
}
