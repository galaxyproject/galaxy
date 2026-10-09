import { getFakeAnonymousUser, getFakeRegisteredUser } from "@tests/test-data";
import { getFakeServiceCredentialGroup, getFakeUserServiceCredentials } from "@tests/test-data/userCredentials";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

const { server, http } = useServerMock();

describe("useUserToolCredentials", () => {
    let credentialsGroup: ServiceCredentialGroupResponse;
    let requiredService: UserServiceCredentialsResponse;
    let optionalService: UserServiceCredentialsResponse;
    let userStore: ReturnType<typeof useUserStore>;
    let toolsServiceCredentialsDefinitionsStore: ReturnType<typeof useToolsServiceCredentialsDefinitionsStore>;
    let userToolsServiceCredentialsStore: ReturnType<typeof useUserToolsServiceCredentialsStore>;

    beforeEach(() => {
        setupTestPinia();

        userStore = useUserStore();
        toolsServiceCredentialsDefinitionsStore = useToolsServiceCredentialsDefinitionsStore();
        userToolsServiceCredentialsStore = useUserToolsServiceCredentialsStore();

        userStore.currentUser = getFakeRegisteredUser({
            id: TEST_USER_ID,
            email: "test@example.com",
            username: "testuser",
            nice_total_disk_usage: "0 bytes",
            quota_percent: 0,
            quota: "0 bytes",
        });
        credentialsGroup = getFakeServiceCredentialGroup({
            variables: [{ name: "bucket_name", value: "my-test-bucket" }],
        });
        requiredService = getFakeUserServiceCredentials({ groups: [credentialsGroup] });
        optionalService = getFakeUserServiceCredentials({
            id: "service-456",
            name: "azure-blob",
            current_group_id: null,
            groups: [
                getFakeServiceCredentialGroup({
                    id: "group-456",
                    name: "Azure Group",
                    variables: [{ name: "account_name", value: "test-account" }],
                    secrets: [{ name: "account_key", is_set: false }],
                }),
            ],
        });

        toolsServiceCredentialsDefinitionsStore.setToolServiceCredentialsDefinitionFor(
            TEST_TOOL_ID,
            TEST_TOOL_VERSION,
            [TEST_SERVICE_DEFINITION, TEST_OPTIONAL_SERVICE_DEFINITION],
        );

        server.use(
            http.get("/api/users/{user_id}/credentials", ({ query, response }) => {
                const sourceType = query.get("source_type");
                const sourceId = query.get("source_id");
                const sourceVersion = query.get("source_version");

                if (sourceType === "tool" && sourceId === TEST_TOOL_ID && sourceVersion === TEST_TOOL_VERSION) {
                    return response(200).json([requiredService, optionalService]);
                }
                return response(200).json([]);
            }),
        );
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe("initialization", () => {
        it("describes both required and optional services for the requested tool", () => {
            const { sourceCredentialsDefinition } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            expect(sourceCredentialsDefinition.value.sourceType).toBe("tool");
            expect(sourceCredentialsDefinition.value.sourceId).toBe(TEST_TOOL_ID);
            expect(sourceCredentialsDefinition.value.services.size).toBe(2);
            expect(sourceCredentialsDefinition.value.services.has("aws-s3-1.0")).toBe(true);
            expect(sourceCredentialsDefinition.value.services.has("azure-blob-1.0")).toBe(true);
        });

        it("starts with unfetched credentials and a warning for required services", () => {
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
        it("fetches both required and optional services for the current tool", async () => {
            const { checkUserCredentials, currentUserToolServices } = useUserToolCredentials(
                TEST_TOOL_ID,
                TEST_TOOL_VERSION,
            );

            await checkUserCredentials();

            expect(currentUserToolServices.value).toHaveLength(2);
            expect(currentUserToolServices.value![0]).toEqual(requiredService);
            expect(currentUserToolServices.value![1]).toEqual(optionalService);
        });

        it("leaves credentials unfetched for an anonymous user", async () => {
            userStore.currentUser = getFakeAnonymousUser();
            const { checkUserCredentials, currentUserToolServices } = useUserToolCredentials(
                TEST_TOOL_ID,
                TEST_TOOL_VERSION,
            );

            await checkUserCredentials();

            expect(currentUserToolServices.value).toBeUndefined();
        });

        it("uses cached services instead of fetching them again", async () => {
            const { checkUserCredentials } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            await checkUserCredentials();

            const fetchSpy = vi.spyOn(userToolsServiceCredentialsStore, "fetchAllUserToolServices");

            await checkUserCredentials();

            expect(fetchSpy).not.toHaveBeenCalled();
        });
    });

    describe("computed properties", () => {
        beforeEach(async () => {
            const { checkUserCredentials } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);
            await checkUserCredentials();
        });

        it("finds the user service by name and version", () => {
            const { userServiceFor } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            const serviceIdentifier: ServiceCredentialsIdentifier = { name: "aws-s3", version: "1.0" };
            const service = userServiceFor.value(serviceIdentifier);

            expect(service).toEqual(requiredService);
        });

        it("returns the credential groups for the requested service", () => {
            const { userServiceGroupsFor } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            const serviceIdentifier: ServiceCredentialsIdentifier = { name: "aws-s3", version: "1.0" };
            const groups = userServiceGroupsFor.value(serviceIdentifier);

            expect(groups).toEqual([credentialsGroup]);
        });

        it("reports incomplete credentials when the optional service has no selected group", () => {
            const { hasUserProvidedAllServiceCredentials } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            expect(hasUserProvidedAllServiceCredentials.value).toBe(false);
        });

        it("reports required credentials as provided when only the optional group is missing", () => {
            const { hasUserProvidedAllRequiredServiceCredentials } = useUserToolCredentials(
                TEST_TOOL_ID,
                TEST_TOOL_VERSION,
            );

            expect(hasUserProvidedAllRequiredServiceCredentials.value).toBe(true);
        });

        it("requires no credentials for a tool with only optional services", () => {
            const OPTIONAL_ONLY_TOOL_ID = "optional-only-tool";
            const OPTIONAL_ONLY_TOOL_VERSION = "1.0.0";

            toolsServiceCredentialsDefinitionsStore.setToolServiceCredentialsDefinitionFor(
                OPTIONAL_ONLY_TOOL_ID,
                OPTIONAL_ONLY_TOOL_VERSION,
                [TEST_OPTIONAL_SERVICE_DEFINITION],
            );

            userToolsServiceCredentialsStore.userToolsServices[
                `${TEST_USER_ID}-${OPTIONAL_ONLY_TOOL_ID}-${OPTIONAL_ONLY_TOOL_VERSION}`
            ] = [];

            const { hasUserProvidedAllRequiredServiceCredentials, toolHasRequiredServiceCredentials } =
                useUserToolCredentials(OPTIONAL_ONLY_TOOL_ID, OPTIONAL_ONLY_TOOL_VERSION);

            expect(toolHasRequiredServiceCredentials.value).toBe(false);
            expect(hasUserProvidedAllRequiredServiceCredentials.value).toBe(true);
        });

        it("reports no optional credentials when its service has no selected group", () => {
            const { hasUserProvidedSomeOptionalServiceCredentials } = useUserToolCredentials(
                TEST_TOOL_ID,
                TEST_TOOL_VERSION,
            );

            expect(hasUserProvidedSomeOptionalServiceCredentials.value).toBe(false);
        });

        it("identifies a tool with a required service", () => {
            const { toolHasRequiredServiceCredentials } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            expect(toolHasRequiredServiceCredentials.value).toBe(true);
        });

        it("shows success when all required credentials are provided", () => {
            const { statusVariant } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            expect(statusVariant.value).toBe("success");
        });
    });

    describe("utility functions", () => {
        it("finds a service definition by name and version", () => {
            const { getToolServiceCredentialsDefinitionFor } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            const serviceIdentifier: ServiceCredentialsIdentifier = { name: "aws-s3", version: "1.0" };
            const definition = getToolServiceCredentialsDefinitionFor(serviceIdentifier);

            expect(definition).toEqual(TEST_SERVICE_DEFINITION);
        });

        it("identifies the missing service and tool in its error", () => {
            const { getToolServiceCredentialsDefinitionFor } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            const serviceIdentifier: ServiceCredentialsIdentifier = { name: "non-existent", version: "1.0" };

            expect(() => getToolServiceCredentialsDefinitionFor(serviceIdentifier)).toThrow(
                `No definition found for credential service 'non-existent-1.0' in tool ${TEST_TOOL_ID}@${TEST_TOOL_VERSION}`,
            );
        });

        it("builds group inputs with saved variables and masked secrets", () => {
            const { buildGroupsFromUserCredentials } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            const groups = buildGroupsFromUserCredentials(TEST_SERVICE_DEFINITION, requiredService);

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
        it("shows info while credentials are fetching and clears it afterward", async () => {
            const { statusVariant } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            // isBusy is read-only outside the store, so make it busy for real: the
            // fetch sets it before its first await.
            const fetching = userToolsServiceCredentialsStore.fetchAllUserToolsServiceCredentials();
            expect(statusVariant.value).toBe("info");

            await fetching;
            expect(statusVariant.value).not.toBe("info");
        });

        it("shows success when both services have selected groups", () => {
            const serviceWithCurrentGroup: UserServiceCredentialsResponse = {
                ...optionalService,
                current_group_id: "group-456",
            };

            userToolsServiceCredentialsStore.userToolsServices[`${TEST_USER_ID}-${TEST_TOOL_ID}-${TEST_TOOL_VERSION}`] =
                [requiredService, serviceWithCurrentGroup];

            const { statusVariant } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            expect(statusVariant.value).toBe("success");
        });

        it("shows a warning when the required service is missing", () => {
            userToolsServiceCredentialsStore.userToolsServices[`${TEST_USER_ID}-${TEST_TOOL_ID}-${TEST_TOOL_VERSION}`] =
                [optionalService];

            const { statusVariant } = useUserToolCredentials(TEST_TOOL_ID, TEST_TOOL_VERSION);

            expect(statusVariant.value).toBe("warning");
        });
    });
});
