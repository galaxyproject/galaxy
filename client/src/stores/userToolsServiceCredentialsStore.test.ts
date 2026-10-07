import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { reactive } from "vue";

import type { RegisteredUser } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import type { ServiceCredentialGroupPayload, UserServiceCredentialsResponse } from "@/api/userCredentials";
import { setupTestPinia } from "@/stores/testUtils";
import { useUserStore } from "@/stores/userStore";

import { SECRET_PLACEHOLDER, useUserToolsServiceCredentialsStore } from "./userToolsServiceCredentialsStore";

const USER_ID = "test-user-123";
const TOOL_ID = "test-tool";
const TOOL_VERSION = "1.0.0";
const SERVICE = { name: "aws-s3", version: "1.0" };

const GROUP = {
    id: "group-123",
    name: "Test Group",
    update_time: "2023-01-01T00:00:00Z",
    variables: [{ name: "bucket_name", value: "my-bucket" }],
    secrets: [
        { name: "access_key", is_set: true },
        { name: "secret_key", is_set: true },
    ],
};

const USER_SERVICE: UserServiceCredentialsResponse = {
    id: "service-123",
    user_id: USER_ID,
    source_type: "tool",
    source_id: TOOL_ID,
    source_version: TOOL_VERSION,
    ...SERVICE,
    current_group_id: GROUP.id,
    groups: [GROUP],
};

const CURRENT_USER: RegisteredUser = {
    id: USER_ID,
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

const { server, http } = useServerMock();

describe("useUserToolsServiceCredentialsStore", () => {
    let sentBody: ServiceCredentialGroupPayload | undefined;

    beforeEach(() => {
        setupTestPinia();
        useUserStore().currentUser = CURRENT_USER;
        sentBody = undefined;
        server.use(
            http.get("/api/users/{user_id}/credentials", ({ response }) => response(200).json([USER_SERVICE])),
            http.put(
                "/api/users/{user_id}/credentials/{user_credentials_id}/groups/{group_id}",
                async ({ request, response }) => {
                    sentBody = (await request.json()) as ServiceCredentialGroupPayload;
                    return response(200).json(GROUP);
                },
            ),
        );
    });

    afterEach(() => {
        server.resetHandlers();
    });

    describe("updateUserCredentialsForTool", () => {
        it("saves a payload held in reactive editing state", async () => {
            const store = useUserToolsServiceCredentialsStore();
            await store.fetchAllUserToolServices(TOOL_ID, TOOL_VERSION);
            // The credentials editor keeps the payload it edits in reactive state.
            const payload = reactive<ServiceCredentialGroupPayload>({
                name: "Test Group",
                variables: [{ name: "bucket_name", value: "new-bucket" }],
                secrets: [
                    { name: "access_key", value: SECRET_PLACEHOLDER },
                    { name: "secret_key", value: "new-secret" },
                ],
            });

            await store.updateUserCredentialsForTool(TOOL_ID, TOOL_VERSION, SERVICE, GROUP.id, payload);

            expect(sentBody).toEqual({
                name: "Test Group",
                variables: [{ name: "bucket_name", value: "new-bucket" }],
                secrets: [
                    { name: "access_key", value: null },
                    { name: "secret_key", value: "new-secret" },
                ],
            });
            // Placeholders are dropped from the copy that is sent, not from the editor's state.
            expect(payload.secrets[0]!.value).toBe(SECRET_PLACEHOLDER);
        });
    });
});
