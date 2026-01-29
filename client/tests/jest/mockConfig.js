import { useConfig } from "@/composables/config";

jest.mock("composables/config");

export function setupMockConfig(configValues, isConfigLoaded = true) {
    return useConfig.mockReturnValue({
        config: { value: configValues },
        isConfigLoaded: isConfigLoaded,
    });
}
