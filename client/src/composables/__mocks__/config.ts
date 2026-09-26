import { vi } from "vitest";
import { ref } from "vue";

// Default mock config values
const defaultConfig = {
    allow_local_account_creation: true,
    enable_oidc: false,
    mailing_join_addr: "",
    prefer_custos_login: false,
    registration_warning_message: "",
    server_mail_configured: false,
    show_welcome_with_login: false,
    terms_url: "",
    welcome_url: "",
    citation_bibtex: "",
    toolbox_auto_sort: false,
};

const mockConfig = ref({ ...defaultConfig });

export const useConfig = vi.fn(() => ({
    config: mockConfig,
    isConfigLoaded: true,
}));

// Helper function for tests to override config values
export function setMockConfig(config: Record<string, any>) {
    mockConfig.value = { ...mockConfig.value, ...config };
}

// Helper function to reset config to defaults
export function resetMockConfig() {
    mockConfig.value = { ...defaultConfig };
}
