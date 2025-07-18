import type { ServiceCredentialsDefinition, ServiceVariableDefinition, UserCredentials } from "@/api/users";

import { useUserToolCredentials } from "./userToolCredentials";

// Mock the dependencies
jest.mock("@/api", () => ({
    isRegisteredUser: jest.fn((user) => user && user.id !== "anonymous"),
}));

jest.mock("@/stores/userCredentials", () => ({
    useUserCredentialsStore: jest.fn(() => ({
        getAllUserCredentialsForTool: jest.fn(),
        fetchAllUserCredentialsForTool: jest.fn(),
        saveUserCredentialsForTool: jest.fn(),
        deleteCredentialsGroupForTool: jest.fn(),
    })),
}));

jest.mock("@/stores/userStore", () => ({
    useUserStore: jest.fn(() => ({
        currentUser: { id: "test-user" },
        isAnonymous: false,
    })),
}));

jest.mock("./toolCredentials", () => ({
    useToolCredentials: jest.fn(() => ({
        sourceCredentialsDefinition: { value: { sourceType: "tool", sourceId: "test-tool", services: new Map() } },
        hasSomeOptionalCredentials: { value: false },
        hasSomeRequiredCredentials: { value: true },
        hasAnyCredentials: { value: true },
        servicesCount: { value: 1 },
    })),
}));

const baseUserCredentials: UserCredentials = {
    id: "cred-1",
    name: "test-service",
    version: "1.0",
    label: "Test Service",
    description: "A test service",
    source_id: "test-tool",
    source_type: "tool",
    source_version: "1.0",
    user_id: "test-user",
    current_group_name: "default",
    groups: {
        default: {
            id: "group-1",
            name: "default",
            secrets: [],
            variables: [],
        },
    },
    credential_definitions: {
        secrets: [],
        variables: [],
    },
};

describe("useUserToolCredentials", () => {
    const mockSecretDefinition: ServiceVariableDefinition = {
        name: "api_key",
        label: "API Key",
        description: "Your service API key",
        optional: false,
    };

    const mockVariableDefinition: ServiceVariableDefinition = {
        name: "base_url",
        label: "Base URL",
        description: "Service base URL",
        optional: false,
    };

    const mockServiceCredentialsDefinition: ServiceCredentialsDefinition[] = [
        {
            name: "test-service",
            version: "1.0",
            label: "Test Service",
            description: "A test service",
            secrets: [mockSecretDefinition],
            variables: [mockVariableDefinition],
        },
    ];

    const mockUserCredentials: UserCredentials[] = [
        {
            ...baseUserCredentials,
            groups: {
                default: {
                    id: "group-1",
                    name: "default",
                    secrets: [{ id: "secret-1", name: "api_key", is_set: true, value: "***" }],
                    variables: [{ id: "var-1", name: "base_url", is_set: true, value: "https://api.example.com" }],
                },
            },
            credential_definitions: {
                secrets: [mockSecretDefinition],
                variables: [mockVariableDefinition],
            },
        },
    ];

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it("initializes with tool credentials data", () => {
        const {
            sourceCredentialsDefinition,
            hasSomeOptionalCredentials,
            hasSomeRequiredCredentials,
            hasAnyCredentials,
            servicesCount,
        } = useUserToolCredentials("test-tool", mockServiceCredentialsDefinition);

        expect(sourceCredentialsDefinition.value.sourceType).toBe("tool");
        expect(sourceCredentialsDefinition.value.sourceId).toBe("test-tool");
        expect(hasSomeRequiredCredentials.value).toBe(true);
        expect(hasSomeOptionalCredentials.value).toBe(false);
        expect(hasAnyCredentials.value).toBe(true);
        expect(servicesCount.value).toBe(1);
    });

    it("initializes with default user credentials state", () => {
        const { userCredentials, isBusy, busyMessage, hasUserProvidedRequiredCredentials } = useUserToolCredentials(
            "test-tool",
            mockServiceCredentialsDefinition
        );

        expect(userCredentials.value).toBeUndefined();
        expect(isBusy.value).toBe(false);
        expect(busyMessage.value).toBe("");
        expect(hasUserProvidedRequiredCredentials.value).toBe(false);
    });

    it("provides correct button title based on credential state", () => {
        const { provideCredentialsButtonTitle, updateUserCredentials } = useUserToolCredentials(
            "test-tool",
            mockServiceCredentialsDefinition
        );

        expect(provideCredentialsButtonTitle.value).toBe("Provide credentials");

        updateUserCredentials(mockUserCredentials);
        expect(provideCredentialsButtonTitle.value).toBe("Manage credentials");
    });

    it("provides correct status variant based on state", () => {
        const { statusVariant, updateUserCredentials } = useUserToolCredentials(
            "test-tool",
            mockServiceCredentialsDefinition
        );

        expect(statusVariant.value).toBe("warning");

        updateUserCredentials(mockUserCredentials);
        expect(statusVariant.value).toBe("success");
    });

    it("detects when user has provided required credentials", () => {
        const { hasUserProvidedRequiredCredentials, updateUserCredentials } = useUserToolCredentials(
            "test-tool",
            mockServiceCredentialsDefinition
        );

        expect(hasUserProvidedRequiredCredentials.value).toBe(false);

        updateUserCredentials(mockUserCredentials);
        expect(hasUserProvidedRequiredCredentials.value).toBe(true);
    });

    it("detects when user has provided all credentials", () => {
        const { hasUserProvidedAllCredentials, updateUserCredentials } = useUserToolCredentials(
            "test-tool",
            mockServiceCredentialsDefinition
        );

        expect(hasUserProvidedAllCredentials.value).toBe(false);

        updateUserCredentials(mockUserCredentials);
        expect(hasUserProvidedAllCredentials.value).toBe(true);
    });

    it("handles incomplete credentials correctly", () => {
        const incompleteCredentials: UserCredentials[] = [
            {
                ...baseUserCredentials,
                groups: {
                    default: {
                        id: "group-1",
                        name: "default",
                        secrets: [{ id: "secret-1", name: "api_key", is_set: false, value: null }], // Missing required secret
                        variables: [{ id: "var-1", name: "base_url", is_set: true, value: "https://api.example.com" }],
                    },
                },
                credential_definitions: {
                    secrets: [mockSecretDefinition],
                    variables: [mockVariableDefinition],
                },
            },
        ];

        const { hasUserProvidedRequiredCredentials, hasUserProvidedAllCredentials, updateUserCredentials } =
            useUserToolCredentials("test-tool", mockServiceCredentialsDefinition);

        updateUserCredentials(incompleteCredentials);

        expect(hasUserProvidedRequiredCredentials.value).toBe(false);
        expect(hasUserProvidedAllCredentials.value).toBe(false);
    });

    it("handles optional credentials correctly", () => {
        const optionalSecretDefinition: ServiceVariableDefinition = {
            ...mockSecretDefinition,
            optional: true,
        };

        const credentialsWithOptional: UserCredentials[] = [
            {
                ...baseUserCredentials,
                groups: {
                    default: {
                        id: "group-1",
                        name: "default",
                        secrets: [{ id: "secret-1", name: "api_key", is_set: false, value: null }], // Optional secret not set
                        variables: [{ id: "var-1", name: "base_url", is_set: true, value: "https://api.example.com" }],
                    },
                },
                credential_definitions: {
                    secrets: [optionalSecretDefinition],
                    variables: [mockVariableDefinition],
                },
            },
        ];

        const { hasUserProvidedRequiredCredentials, updateUserCredentials } = useUserToolCredentials(
            "test-tool",
            mockServiceCredentialsDefinition
        );

        updateUserCredentials(credentialsWithOptional);

        // Should be true because the secret is optional
        expect(hasUserProvidedRequiredCredentials.value).toBe(true);
    });

    it("exposes user store properties", () => {
        const { isAnonymous } = useUserToolCredentials("test-tool", mockServiceCredentialsDefinition);

        expect(isAnonymous.value).toBe(false);
    });
});
