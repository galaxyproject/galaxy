import { afterEach, beforeEach, describe, expect, it } from "vitest";

import type { RegisteredUser } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import type { ServiceCredentialsDefinition, UserServiceCredentialsResponse } from "@/api/userCredentials";
import { setupTestPinia } from "@/stores/testUtils";
import { useToolsServiceCredentialsDefinitionsStore } from "@/stores/toolsServiceCredentialsDefinitionsStore";
import { useUserStore } from "@/stores/userStore";
import { useUserToolsServiceCredentialsStore } from "@/stores/userToolsServiceCredentialsStore";

import { useUserMultiToolCredentials } from "./userMultiToolCredentials";
import { useUserToolCredentials } from "./userToolCredentials";

const USER_ID = "test-user-123";
const REQUIRED_TOOL = { toolId: "required-tool", toolVersion: "1.0.0" };
const OPTIONAL_TOOL = { toolId: "optional-tool", toolVersion: "1.0.0" };

function serviceDefinition(name: string, optional: boolean): ServiceCredentialsDefinition {
    return {
        name,
        version: "1.0",
        description: name,
        label: name,
        optional,
        variables: [],
        secrets: [{ name: "token", label: "Token", description: "Token", optional: false }],
    };
}

function savedService(tool: typeof REQUIRED_TOOL, name: string): UserServiceCredentialsResponse {
    return {
        id: `${name}-service`,
        user_id: USER_ID,
        source_type: "tool",
        source_id: tool.toolId,
        source_version: tool.toolVersion,
        name,
        version: "1.0",
        current_group_id: `${name}-group`,
        groups: [
            {
                id: `${name}-group`,
                name: "default",
                update_time: "2023-01-01T00:00:00Z",
                variables: [],
                secrets: [{ name: "token", is_set: true }],
            },
        ],
    };
}

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

/** checkAllUserCredentials only fetches once, so a later change has to refresh the store. */
async function refetch(tool: typeof REQUIRED_TOOL) {
    await useUserToolsServiceCredentialsStore().fetchAllUserToolServices(tool.toolId, tool.toolVersion);
}

describe("useUserMultiToolCredentials", () => {
    let savedServices: UserServiceCredentialsResponse[];

    beforeEach(() => {
        setupTestPinia();
        useUserStore().currentUser = CURRENT_USER;
        const definitions = useToolsServiceCredentialsDefinitionsStore();
        definitions.setToolServiceCredentialsDefinitionFor(REQUIRED_TOOL.toolId, REQUIRED_TOOL.toolVersion, [
            serviceDefinition("required-service", false),
        ]);
        definitions.setToolServiceCredentialsDefinitionFor(OPTIONAL_TOOL.toolId, OPTIONAL_TOOL.toolVersion, [
            serviceDefinition("optional-service", true),
        ]);

        savedServices = [];
        server.use(
            http.get("/api/users/{user_id}/credentials", ({ query, response }) => {
                return response(200).json(savedServices.filter((s) => s.source_id === query.get("source_id")));
            }),
        );
    });

    afterEach(() => {
        server.resetHandlers();
    });

    it("reports missing required credentials, like the single-tool check does", async () => {
        const single = useUserToolCredentials(REQUIRED_TOOL.toolId, REQUIRED_TOOL.toolVersion);
        const multi = useUserMultiToolCredentials([REQUIRED_TOOL]);
        await multi.checkAllUserCredentials();

        expect(single.hasUserProvidedAllRequiredServiceCredentials.value).toBe(false);
        expect(multi.someToolsHasRequiredServiceCredentials.value).toBe(true);
        expect(multi.hasUserProvidedAllRequiredToolsServiceCredentials.value).toBe(false);
        expect(multi.hasUserProvidedAllToolsServiceCredentials.value).toBe(false);
        expect(multi.statusVariant.value).toBe("warning");
    });

    it("follows required credentials being supplied and removed", async () => {
        const multi = useUserMultiToolCredentials([REQUIRED_TOOL]);
        await multi.checkAllUserCredentials();
        expect(multi.hasUserProvidedAllRequiredToolsServiceCredentials.value).toBe(false);

        savedServices = [savedService(REQUIRED_TOOL, "required-service")];
        await refetch(REQUIRED_TOOL);
        expect(multi.hasUserProvidedAllRequiredToolsServiceCredentials.value).toBe(true);
        expect(multi.statusVariant.value).toBe("success");

        savedServices = [];
        await refetch(REQUIRED_TOOL);
        expect(multi.hasUserProvidedAllRequiredToolsServiceCredentials.value).toBe(false);
        expect(multi.statusVariant.value).toBe("warning");
    });

    it("tracks optional credentials separately from required ones", async () => {
        const multi = useUserMultiToolCredentials([OPTIONAL_TOOL]);
        await multi.checkAllUserCredentials();
        expect(multi.someToolsHasRequiredServiceCredentials.value).toBe(false);
        expect(multi.hasUserProvidedSomeOptionalToolsServiceCredentials.value).toBe(false);

        savedServices = [savedService(OPTIONAL_TOOL, "optional-service")];
        await refetch(OPTIONAL_TOOL);
        expect(multi.hasUserProvidedSomeOptionalToolsServiceCredentials.value).toBe(true);
    });

    it("only counts as complete once every tool has its required credentials", async () => {
        const otherRequiredTool = { toolId: "other-required-tool", toolVersion: "1.0.0" };
        useToolsServiceCredentialsDefinitionsStore().setToolServiceCredentialsDefinitionFor(
            otherRequiredTool.toolId,
            otherRequiredTool.toolVersion,
            [serviceDefinition("required-service", false)],
        );
        savedServices = [savedService(REQUIRED_TOOL, "required-service")];
        const multi = useUserMultiToolCredentials([REQUIRED_TOOL, otherRequiredTool]);
        await multi.checkAllUserCredentials();

        expect(multi.hasUserProvidedAllRequiredToolsServiceCredentials.value).toBe(false);
    });
});
