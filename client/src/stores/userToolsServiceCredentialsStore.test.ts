import { getFakeRegisteredUser } from "@tests/test-data";
import { getFakeServiceCredentialGroup, getFakeUserServiceCredentials } from "@tests/test-data/userCredentials";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { reactive } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import type { ServiceCredentialGroupPayload } from "@/api/userCredentials";
import { setupTestPinia } from "@/stores/testUtils";
import { useUserStore } from "@/stores/userStore";

import { SECRET_PLACEHOLDER, useUserToolsServiceCredentialsStore } from "./userToolsServiceCredentialsStore";

const USER_ID = "test-user-123";
const TOOL_ID = "test-tool";
const TOOL_VERSION = "1.0.0";
const SERVICE = { name: "aws-s3", version: "1.0" };

const GROUP = getFakeServiceCredentialGroup();
const USER_SERVICE = getFakeUserServiceCredentials({ groups: [GROUP] });

const { server, http } = useServerMock();

describe("useUserToolsServiceCredentialsStore", () => {
    let sentBody: ServiceCredentialGroupPayload | undefined;

    beforeEach(() => {
        setupTestPinia();
        useUserStore().currentUser = getFakeRegisteredUser({
            id: USER_ID,
            email: "test@example.com",
            username: "testuser",
            nice_total_disk_usage: "0 bytes",
            quota_percent: 0,
            quota: "0 bytes",
        });
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
