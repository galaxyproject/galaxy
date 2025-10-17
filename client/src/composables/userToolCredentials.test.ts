import flushPromises from "flush-promises";

import type { RegisteredUser } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import type {
    ServiceCredentialGroupResponse,
    ServiceCredentialsDefinition,
    ServiceCredentialsIdentifier,
    UserServiceCredentialsResponse,
} from "@/api/userCredentials";
import { setupTestPinia } from "@/stores/testUtils";
import { useToolsServiceCredentialsDefinitionsStore } from "@/stores/toolsServiceCredentialsDefinitionsStore";
import { useUserStore } from "@/stores/userStore";
import { useUserToolsServiceCredentialsStore } from "@/stores/userToolsServiceCredentialsStore";

import { useUserToolCredentials } from "./userToolCredentials";

// Mock data
const TEST_TOOL_ID = "test-tool";
const TEST_TOOL_VERSION = "1.0.0";
const TEST_USER_ID = "test-user-123";

const TEST_SERVICE_DEFINITION: ServiceCredentialsDefinition = {
    name: "aws-s3",
    version: "1.0",
    description: "AWS S3 Service",
    label: "AWS S3",
    optional: false,
    variables: [
        {
            name: "bucket_name",
            label: "Bucket Name",
            description: "The S3 bucket name",
            optional: false,
        },
    ],
    secrets: [
        {
            name: "access_key",
            label: "Access Key",
            description: "AWS Access Key",
            optional: false,
        },
        {
            name: "secret_key",
            label: "Secret Key",
            description: "AWS Secret Key",
            optional: false,
        },
    ],
};

const TEST_OPTIONAL_SERVICE_DEFINITION: ServiceCredentialsDefinition = {
    name: "azure-blob",
    version: "1.0",
    description: "Azure Blob Storage",
    label: "Azure Blob",
    optional: true,
    variables: [
        {
            name: "account_name",
            label: "Account Name",
            description: "Azure storage account name",
            optional: false,
        },
    ],
    secrets: [
        {
            name: "account_key",
            label: "Account Key",
            description: "Azure storage account key",
            optional: false,
        },
    ],
};

const TEST_CREDENTIALS_GROUP: ServiceCredentialGroupResponse = {
    id: "group-123",
    name: "Test Group",
    update_time: "2023-01-01T00:00:00Z",
    variables: [
        {
            name: "bucket_name",
            value: "my-test-bucket",
        },
    ],
    secrets: [
        {
            name: "access_key",
            is_set: true,
        },
        {
            name: "secret_key",
            is_set: true,
        },
    ],
};

const TEST_USER_SOURCE_SERVICE: UserServiceCredentialsResponse = {
    id: "service-123",
    user_id: TEST_USER_ID,
    source_type: "tool",
    source_id: TEST_TOOL_ID,
    source_version: TEST_TOOL_VERSION,
    name: "aws-s3",
    version: "1.0",
    current_group_id: "group-123",
    groups: [TEST_CREDENTIALS_GROUP],
};

const TEST_USER_SOURCE_SERVICE_NO_CURRENT_GROUP: UserServiceCredentialsResponse = {
    id: "service-456",
    user_id: TEST_USER_ID,
    source_type: "tool",
    source_id: TEST_TOOL_ID,
    source_version: TEST_TOOL_VERSION,
    name: "azure-blob",
    version: "1.0",
    current_group_id: null,
    groups: [
        {
            id: "group-456",
            name: "Azure Group",
            update_time: "2023-01-01T00:00:00Z",
            variables: [{ name: "account_name", value: "test-account" }],
            secrets: [{ name: "account_key", is_set: false }],
        },
    ],
};

const TEST_CURRENT_USER: RegisteredUser = {
    id: TEST_USER_ID,
    email: "test@example.com",
    username: "testuser",
    is_admin: false,
    preferences: {},
    total_disk_usage: 0,
    nice_total_disk_usage: "0 bytes",
    quota_percent: 0,
    quota: "0 bytes",
    deleted: false,
    purged: false,
    isAnonymous: false as const,
};

// Mock the server responses
const { server, http } = useServerMock();

describe("useUserToolCredentials", () => {
    let userStore: ReturnType<typeof useUserStore>;
    let toolsServiceCredentialsDefinitionsStore: ReturnType<typeof useToolsServiceCredentialsDefinitionsStore>;
    let userToolsServiceCredentialsStore: ReturnType<typeof useUserToolsServiceCredentialsStore>;

    beforeEach(() => {
        setupTestPinia();

        userStore = useUserStore();
        toolsServiceCredentialsDefinitionsStore = useToolsServiceCredentialsDefinitionsStore();
        userToolsServiceCredentialsStore = useUserToolsServiceCredentialsStore();

        // Set up current user
        userStore.currentUser = TEST_CURRENT_USER;

        // Set up service definitions
        toolsServiceCredentialsDefinitionsStore.setToolServiceCredentialsDefinitionFor(
            TEST_TOOL_ID,
            TEST_TOOL_VERSION,
            [TEST_SERVICE_DEFINITION, TEST_OPTIONAL_SERVICE_DEFINITION],
        );

        // Mock API endpoints
        server.use(
            http.get("/api/users/{user_id}/credentials", ({ query, response }) => {
                const sourceType = query.get("source_type");
                const sourceId = query.get("source_id");
                const sourceVersion = query.get("source_version");

                if (sourceType === "tool" && sourceId === TEST_TOOL_ID && sourceVersion === TEST_TOOL_VERSION) {
                    return response(200).json([TEST_USER_SOURCE_SERVICE, TEST_USER_SOURCE_SERVICE_NO_CURRENT_GROUP]);
                }
                return response(200).json([]);
            }),

            http.post("/api/users/{user_id}/credentials", ({ response }) => {
                return response(200).json(TEST_CREDENTIALS_GROUP);
            }),

            http.put("/api/users/{user_id}/credentials/{user_credentials_id}/groups/{group_id}", ({ response }) => {
                return response(200).json({
                    ...TEST_CREDENTIALS_GROUP,
                    variables: [{ name: "bucket_name", value: "updated-bucket" }],
                });
            }),

            http.delete("/api/users/{user_id}/credentials/{user_credentials_id}/groups/{group_id}", ({ response }) => {
                return response(204).empty();
            }),

            http.put("/api/users/{user_id}/credentials", ({ response }) => {
                return response(204).empty();
            }),
        );
    });

    afterEach(() => {
        server.resetHandlers();
    });

    describe("initialization", () => {
        it("should initialize with correct tool ID and version", () => {
            const { sourceCredentialsDefinition } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            expect(sourceCredentialsDefinition.value.sourceType).toBe("tool");
            expect(sourceCredentialsDefinition.value.sourceId).toBe(TEST_TOOL_ID);
            expect(sourceCredentialsDefinition.value.services.size).toBe(2);
            expect(sourceCredentialsDefinition.value.services.has("aws-s3-1.0")).toBe(true);
            expect(sourceCredentialsDefinition.value.services.has("azure-blob-1.0")).toBe(true);
        });

        it("should have proper reactive state initially", () => {
            const {
                currentUserToolServices,
                hasUserProvidedAllServiceCredentials,
                hasUserProvidedAllRequiredServiceCredentials,
                toolHasRequiredServiceCredentials,
                statusVariant,
            } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            expect(currentUserToolServices.value).toBeUndefined();
            expect(hasUserProvidedAllServiceCredentials.value).toBe(false);
            expect(hasUserProvidedAllRequiredServiceCredentials.value).toBe(false);
            expect(toolHasRequiredServiceCredentials.value).toBe(true);
            expect(statusVariant.value).toBe("warning");
        });
    });

    describe("checkUserCredentials", () => {
        it("should fetch user credentials successfully", async () => {
            const { checkUserCredentials, currentUserToolServices } = useUserToolCredentials(
                TEST_TOOL_ID,
                TEST_TOOL_VERSION,
            );

            await checkUserCredentials();
            await flushPromises();

            expect(currentUserToolServices.value).toHaveLength(2);
            expect(currentUserToolServices.value![0]).toEqual(TEST_USER_SOURCE_SERVICE);
            expect(currentUserToolServices.value![1]).toEqual(TEST_USER_SOURCE_SERVICE_NO_CURRENT_GROUP);
        });

        it("should not fetch if user is not registered", async () => {
            userStore.currentUser = { isAnonymous: true, total_disk_usage: 0, nice_total_disk_usage: "0 bytes" };
            const { checkUserCredentials, currentUserToolServices } = useUserToolCredentials(
                TEST_TOOL_ID,
                TEST_TOOL_VERSION,
            );

            await checkUserCredentials();
            await flushPromises();

            expect(currentUserToolServices.value).toBeUndefined();
        });

        it("should not fetch if credentials already exist", async () => {
            const { checkUserCredentials } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            // First call
            await checkUserCredentials();
            await flushPromises();

            // Mock the store to track if fetch was called again
            const fetchSpy = jest.spyOn(userToolsServiceCredentialsStore, "fetchAllUserToolServices");

            // Second call
            await checkUserCredentials();
            await flushPromises();

            expect(fetchSpy).not.toHaveBeenCalled();
        });
    });

    describe("computed properties", () => {
        beforeEach(async () => {
            const { checkUserCredentials } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);
            await checkUserCredentials();
            await flushPromises();
        });

        it("should correctly compute userServiceFor", () => {
            const { userServiceFor } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            const serviceIdentifier: ServiceCredentialsIdentifier = { name: "aws-s3", version: "1.0" };
            const service = userServiceFor.value(serviceIdentifier);

            expect(service).toEqual(TEST_USER_SOURCE_SERVICE);
        });

        it("should correctly compute userServiceGroupsFor", () => {
            const { userServiceGroupsFor } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            const serviceIdentifier: ServiceCredentialsIdentifier = { name: "aws-s3", version: "1.0" };
            const groups = userServiceGroupsFor.value(serviceIdentifier);

            expect(groups).toEqual([TEST_CREDENTIALS_GROUP]);
        });

        it("should correctly compute hasUserProvidedAllServiceCredentials", () => {
            const { hasUserProvidedAllServiceCredentials } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            // One service has current group, one doesn't
            expect(hasUserProvidedAllServiceCredentials.value).toBe(false);
        });

        it("should correctly compute hasUserProvidedAllRequiredServiceCredentials", () => {
            const { hasUserProvidedAllRequiredServiceCredentials } = useUserToolCredentials(
                TEST_TOOL_ID,
                TEST_TOOL_VERSION,
            );

            // Required service (aws-s3) has current group, optional service (azure-blob) doesn't
            expect(hasUserProvidedAllRequiredServiceCredentials.value).toBe(true);
        });

        it("should correctly compute hasUserProvidedSomeOptionalServiceCredentials", () => {
            const { hasUserProvidedSomeOptionalServiceCredentials } = useUserToolCredentials(
                TEST_TOOL_ID,
                TEST_TOOL_VERSION,
            );

            // Optional service (azure-blob) doesn't have current group
            expect(hasUserProvidedSomeOptionalServiceCredentials.value).toBe(false);
        });

        it("should correctly compute toolHasRequiredServiceCredentials", () => {
            const { toolHasRequiredServiceCredentials } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            expect(toolHasRequiredServiceCredentials.value).toBe(true);
        });

        it("should correctly compute statusVariant", () => {
            const { statusVariant } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            // Should be success since required credentials are provided
            expect(statusVariant.value).toBe("success");
        });
    });

    describe("utility functions", () => {
        it("should get service credentials definition by key", () => {
            const { getToolServiceCredentialsDefinitionFor } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            const serviceIdentifier: ServiceCredentialsIdentifier = { name: "aws-s3", version: "1.0" };
            const definition = getToolServiceCredentialsDefinitionFor(serviceIdentifier);

            expect(definition).toEqual(TEST_SERVICE_DEFINITION);
        });

        it("should throw error for non-existent service definition", () => {
            const { getToolServiceCredentialsDefinitionFor } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            const serviceIdentifier: ServiceCredentialsIdentifier = { name: "non-existent", version: "1.0" };

            expect(() => getToolServiceCredentialsDefinitionFor(serviceIdentifier)).toThrow(
                `No definition found for credential service 'non-existent-1.0' in tool ${TEST_TOOL_ID}@${TEST_TOOL_VERSION}`,
            );
        });

        it("should build groups from user credentials", () => {
            const { buildGroupsFromUserCredentials } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            const groups = buildGroupsFromUserCredentials(TEST_SERVICE_DEFINITION, TEST_USER_SOURCE_SERVICE);

            expect(groups).toHaveLength(1);
            expect(groups[0]?.name).toBe("Test Group");
            expect(groups[0]?.variables).toHaveLength(1);
            expect(groups[0]?.variables[0]?.name).toBe("bucket_name");
            expect(groups[0]?.variables[0]?.value).toBe("my-test-bucket");
            expect(groups[0]?.secrets).toHaveLength(2);
            expect(groups[0]?.secrets[0]?.name).toBe("access_key");
            expect(groups[0]?.secrets[0]?.value).toBe("********");
        });
    });

    describe("status variant computation", () => {
        it("should return info when busy", () => {
            // Mock the isBusy property to return true
            jest.spyOn(userToolsServiceCredentialsStore, "isBusy", "get").mockReturnValue(true);

            const { statusVariant } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            expect(statusVariant.value).toBe("info");
        });

        it("should return success when all credentials provided", async () => {
            // Set up both services with current groups
            const serviceWithCurrentGroup: UserServiceCredentialsResponse = {
                ...TEST_USER_SOURCE_SERVICE_NO_CURRENT_GROUP,
                current_group_id: "group-456",
            };

            userToolsServiceCredentialsStore.userToolsServices[`${TEST_USER_ID}-${TEST_TOOL_ID}-${TEST_TOOL_VERSION}`] =
                [TEST_USER_SOURCE_SERVICE, serviceWithCurrentGroup];

            const { statusVariant } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            expect(statusVariant.value).toBe("success");
        });

        it("should return warning when not all credentials provided", () => {
            userToolsServiceCredentialsStore.userToolsServices[`${TEST_USER_ID}-${TEST_TOOL_ID}-${TEST_TOOL_VERSION}`] =
                [TEST_USER_SOURCE_SERVICE_NO_CURRENT_GROUP];

            const { statusVariant } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            expect(statusVariant.value).toBe("warning");
        });
    });
});
