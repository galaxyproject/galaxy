import type { ServiceCredentialsDefinition, ServiceVariableDefinition, UserCredentials } from "@/api/users";

import { useUserToolCredentials } from "./userToolCredentials";

// Mock the dependencies
jest.mock("@/api", () => ({
    isRegisteredUser: jest.fn((user) => user && user.id !== "anonymous"),
}));

jest.mock("@/stores/userCredentials", () => ({
    SECRET_PLACEHOLDER: "***",
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
    useToolCredentials: jest.fn(() => {
        const servicesMap = new Map();
        servicesMap.set("test-service-1.0", {
            name: "test-service",
            version: "1.0",
            label: "Test Service",
            description: "A test service",
            secrets: [
                {
                    name: "api_key",
                    label: "API Key",
                    description: "Your service API key",
                    optional: false,
                },
            ],
            variables: [
                {
                    name: "base_url",
                    label: "Base URL",
                    description: "Service base URL",
                    optional: false,
                },
            ],
        });

        return {
            sourceCredentialsDefinition: {
                value: {
                    sourceType: "tool",
                    sourceId: "test-tool",
                    services: servicesMap,
                },
            },
            hasSomeOptionalCredentials: { value: false },
            hasSomeRequiredCredentials: { value: true },
            hasAnyCredentials: { value: true },
            servicesCount: { value: 1 },
        };
    }),
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
        } = useUserToolCredentials("test-tool", "1.0", mockServiceCredentialsDefinition);

        expect(sourceCredentialsDefinition.value.sourceType).toBe("tool");
        expect(sourceCredentialsDefinition.value.sourceId).toBe("test-tool");
        expect(hasSomeRequiredCredentials.value).toBe(true);
        expect(hasSomeOptionalCredentials.value).toBe(false);
        expect(hasAnyCredentials.value).toBe(true);
        expect(servicesCount.value).toBe(1);
    });

    it("initializes with default user credentials state", () => {
        const { userCredentials, mutableUserCredentials, isBusy, busyMessage, hasUserProvidedRequiredCredentials } =
            useUserToolCredentials("test-tool", "1.0", mockServiceCredentialsDefinition);

        expect(userCredentials.value).toBeUndefined();
        expect(mutableUserCredentials.value).toBeDefined();
        expect(mutableUserCredentials.value.source_type).toBe("tool");
        expect(mutableUserCredentials.value.source_id).toBe("test-tool");
        expect(mutableUserCredentials.value.source_version).toBe("1.0");
        expect(isBusy.value).toBe(false);
        expect(busyMessage.value).toBe("");
        expect(hasUserProvidedRequiredCredentials.value).toBe(false);
    });

    it("provides correct button title based on credential state", () => {
        const { provideCredentialsButtonTitle, updateUserCredentials } = useUserToolCredentials(
            "test-tool",
            "1.0",
            mockServiceCredentialsDefinition
        );

        expect(provideCredentialsButtonTitle.value).toBe("Provide credentials");

        updateUserCredentials(mockUserCredentials);
        expect(provideCredentialsButtonTitle.value).toBe("Manage credentials");
    });

    it("provides correct status variant based on state", () => {
        const { statusVariant, updateUserCredentials } = useUserToolCredentials(
            "test-tool",
            "1.0",
            mockServiceCredentialsDefinition
        );

        expect(statusVariant.value).toBe("warning");

        updateUserCredentials(mockUserCredentials);
        expect(statusVariant.value).toBe("success");
    });

    it("detects when user has provided required credentials", () => {
        const { hasUserProvidedRequiredCredentials, updateUserCredentials } = useUserToolCredentials(
            "test-tool",
            "1.0",
            mockServiceCredentialsDefinition
        );

        expect(hasUserProvidedRequiredCredentials.value).toBe(false);

        updateUserCredentials(mockUserCredentials);
        expect(hasUserProvidedRequiredCredentials.value).toBe(true);
    });

    it("detects when user has provided all credentials", () => {
        const { hasUserProvidedAllCredentials, updateUserCredentials } = useUserToolCredentials(
            "test-tool",
            "1.0",
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
            useUserToolCredentials("test-tool", "1.0", mockServiceCredentialsDefinition);

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
            "1.0",
            mockServiceCredentialsDefinition
        );

        updateUserCredentials(credentialsWithOptional);

        // Should be true because the secret is optional
        expect(hasUserProvidedRequiredCredentials.value).toBe(true);
    });

    it("creates mutable user credentials payload correctly", () => {
        const { mutableUserCredentials } = useUserToolCredentials("test-tool", "1.0", mockServiceCredentialsDefinition);

        expect(mutableUserCredentials.value.source_type).toBe("tool");
        expect(mutableUserCredentials.value.source_id).toBe("test-tool");
        expect(mutableUserCredentials.value.source_version).toBe("1.0");
        expect(mutableUserCredentials.value.credentials).toHaveLength(1);

        // Check the default structure when no user credentials exist
        const credential = mutableUserCredentials.value.credentials[0];
        expect(credential!.name).toBe("test-service");
        expect(credential!.version).toBe("1.0");
        expect(credential!.current_group).toBe("default");
        expect(credential!.groups).toHaveLength(1);

        const group = credential!.groups[0];
        expect(group!.name).toBe("default");
        expect(group!.variables).toHaveLength(1);
        expect(group!.secrets).toHaveLength(1);

        // Variables should have null values initially
        expect(group!.variables[0]!.name).toBe("base_url");
        expect(group!.variables[0]!.value).toBeNull();

        // Secrets should have null values initially
        expect(group!.secrets[0]!.name).toBe("api_key");
        expect(group!.secrets[0]!.value).toBeNull();
    });

    it("handles mutable credentials with existing user credentials", () => {
        const { updateUserCredentials, mutableUserCredentials, refreshMutableCredentials } = useUserToolCredentials(
            "test-tool",
            "1.0",
            mockServiceCredentialsDefinition
        );

        // Update with user credentials
        updateUserCredentials(mockUserCredentials);

        refreshMutableCredentials();

        // The mutable credentials structure should be available for editing
        expect(mutableUserCredentials.value).toBeDefined();
        expect(mutableUserCredentials.value.source_type).toBe("tool");
        expect(mutableUserCredentials.value.source_id).toBe("test-tool");
        expect(mutableUserCredentials.value.source_version).toBe("1.0");

        // Check that credentials are properly structured
        expect(mutableUserCredentials.value.credentials).toHaveLength(1);

        const credential = mutableUserCredentials.value.credentials[0];
        expect(credential).toBeDefined();
        expect(credential!.name).toBe("test-service");
        expect(credential!.version).toBe("1.0");
        expect(credential!.current_group).toBe("default");

        // Check groups structure
        expect(credential!.groups).toHaveLength(1);
        const group = credential!.groups[0];
        expect(group).toBeDefined();
        expect(group!.name).toBe("default");

        // Check variables are correctly mapped
        expect(group!.variables).toHaveLength(1);
        const variable = group!.variables[0];
        expect(variable).toBeDefined();
        expect(variable!.name).toBe("base_url");
        expect(variable!.value).toBe("https://api.example.com");

        // Check secrets are correctly mapped
        expect(group!.secrets).toHaveLength(1);
        const secret = group!.secrets[0];
        expect(secret).toBeDefined();
        expect(secret!.name).toBe("api_key");
        expect(secret!.value).toBe("***"); // Should use SECRET_PLACEHOLDER when is_set is true
        if ("alreadySet" in secret!) {
            expect((secret as { alreadySet?: boolean }).alreadySet).toBe(true);
        }
    });
});
