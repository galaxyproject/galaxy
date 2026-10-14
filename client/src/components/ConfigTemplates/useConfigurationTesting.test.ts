import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import type { PluginStatus } from "@/api/configTemplates";
import type { UserConcreteObjectStore } from "@/components/ObjectStore/Instances/types";

import { OK_PLUGIN_STATUS, STANDARD_OBJECT_STORE_TEMPLATE } from "./test_fixtures";
import {
    useConfigurationTemplateCreation,
    useConfigurationTemplateEdit,
    useConfigurationTemplateUpgrade,
} from "./useConfigurationTesting";

const { server, http } = useServerMock();

const INSTANCE: UserConcreteObjectStore = {
    type: "aws_s3",
    name: "moo",
    description: undefined,
    template_id: "moo",
    template_version: 1,
    badges: [],
    variables: { oldvar: "my old value" },
    secrets: ["oldsecret"],
    quota: { enabled: false },
    private: false,
    uuid: "112f889f-72d7-4619-a8e8-510a8c685aa7",
    active: true,
    hidden: false,
    purged: false,
};

const FAILED_CONNECTION_STATUS: PluginStatus = {
    ...OK_PLUGIN_STATUS,
    connection: { state: "not_ok", message: "could not connect" },
};

type TestOutcome = "ok" | "not_ok" | "request_fails";

function mockTestResponse(response: any, outcome: TestOutcome) {
    if (outcome === "request_fails") {
        return response("5XX").json({ err_code: 500, err_msg: "test request failed" }, { status: 500 });
    }
    return response(200).json(outcome === "ok" ? OK_PLUGIN_STATUS : FAILED_CONNECTION_STATUS);
}

function mockInstanceTestAndTrackRequests(outcome: TestOutcome) {
    const testRequests = vi.fn();
    const updateRequests = vi.fn();
    server.use(
        http.post("/api/object_store_instances/{uuid}/test", ({ response }) => {
            testRequests();
            return mockTestResponse(response, outcome);
        }),
        http.put("/api/object_store_instances/{uuid}", ({ response }) => {
            updateRequests();
            return response(200).json(INSTANCE);
        }),
    );
    return { testRequests, updateRequests };
}

function mockCreationTestAndTrackRequests(outcome: TestOutcome) {
    const createRequests = vi.fn();
    server.use(
        http.post("/api/object_store_instances/test", ({ response }) => {
            return mockTestResponse(response, outcome);
        }),
        http.post("/api/object_store_instances", ({ response }) => {
            createRequests();
            return response(200).json(INSTANCE);
        }),
    );
    return createRequests;
}

function useEdit(onUpdated = vi.fn()) {
    const goToIndex = vi.fn();
    const edit = useConfigurationTemplateEdit(
        "storage location",
        ref(INSTANCE),
        ref(STANDARD_OBJECT_STORE_TEMPLATE),
        "/api/object_store_instances/{uuid}/test",
        "/api/object_store_instances/{uuid}",
        () => ({ goToIndex }) as never,
        onUpdated,
    );
    return { ...edit, goToIndex };
}

function useUpgrade() {
    return useConfigurationTemplateUpgrade(
        "storage location",
        ref(INSTANCE),
        ref(STANDARD_OBJECT_STORE_TEMPLATE),
        "/api/object_store_instances/{uuid}/test",
        "/api/object_store_instances/{uuid}",
        () => ({ goToIndex: vi.fn() }) as never,
    );
}

function useCreation() {
    return useConfigurationTemplateCreation(
        "storage location",
        ref(STANDARD_OBJECT_STORE_TEMPLATE),
        ref(undefined),
        "/api/object_store_instances/test",
        "/api/object_store_instances",
        vi.fn(),
    );
}

describe("useConfigurationTemplateEdit", () => {
    it("saves and returns to the index when the configuration test passes", async () => {
        const { updateRequests } = mockInstanceTestAndTrackRequests("ok");
        const onUpdated = vi.fn();
        const { onSubmit, error, showForceActionButton, testResults, goToIndex } = useEdit(onUpdated);

        await onSubmit({});

        expect(updateRequests).toHaveBeenCalledOnce();
        expect(onUpdated).toHaveBeenCalledWith(expect.objectContaining({ uuid: INSTANCE.uuid }));
        expect(goToIndex).toHaveBeenCalledWith({ message: "Updated storage location moo" });
        expect(testResults.value).toEqual(OK_PLUGIN_STATUS);
        expect(error.value).toBeNull();
        expect(showForceActionButton.value).toBe(false);
    });

    it("stops and offers to force the update when the configuration test fails", async () => {
        const { updateRequests } = mockInstanceTestAndTrackRequests("not_ok");
        const { onSubmit, error, showForceActionButton } = useEdit();

        await onSubmit({});

        expect(error.value).toBe("could not connect");
        expect(showForceActionButton.value).toBe(true);
        expect(updateRequests).not.toHaveBeenCalled();
    });

    it("stops and offers to force the update when the test request itself fails", async () => {
        const { updateRequests } = mockInstanceTestAndTrackRequests("request_fails");
        const { onSubmit, error, showForceActionButton } = useEdit();

        await onSubmit({});

        expect(error.value).toBe("test request failed");
        expect(showForceActionButton.value).toBe(true);
        expect(updateRequests).not.toHaveBeenCalled();
    });

    it("saves without testing when forced", async () => {
        const { testRequests, updateRequests } = mockInstanceTestAndTrackRequests("not_ok");
        const { onForceSubmit, goToIndex } = useEdit();

        await onForceSubmit({});

        expect(testRequests).not.toHaveBeenCalled();
        expect(updateRequests).toHaveBeenCalledOnce();
        expect(goToIndex).toHaveBeenCalledOnce();
    });
});

describe("useConfigurationTemplateUpgrade", () => {
    it("stops and offers to force the upgrade when the configuration test fails", async () => {
        const { updateRequests } = mockInstanceTestAndTrackRequests("not_ok");
        const { onSubmit, error, showForceActionButton } = useUpgrade();

        await onSubmit({});

        expect(error.value).toBe("could not connect");
        expect(showForceActionButton.value).toBe(true);
        expect(updateRequests).not.toHaveBeenCalled();
    });

    it("stops and offers to force the upgrade when the test request itself fails", async () => {
        const { updateRequests } = mockInstanceTestAndTrackRequests("request_fails");
        const { onSubmit, error, showForceActionButton } = useUpgrade();

        await onSubmit({});

        expect(error.value).toBe("test request failed");
        expect(showForceActionButton.value).toBe(true);
        expect(updateRequests).not.toHaveBeenCalled();
    });

    it("upgrades without testing when forced", async () => {
        const { testRequests, updateRequests } = mockInstanceTestAndTrackRequests("not_ok");
        const { onForceSubmit } = useUpgrade();

        await onForceSubmit({});

        expect(testRequests).not.toHaveBeenCalled();
        expect(updateRequests).toHaveBeenCalledOnce();
    });
});

describe("useConfigurationTemplateCreation", () => {
    it("reports a failed test request as a verification failure", async () => {
        const createRequests = mockCreationTestAndTrackRequests("request_fails");
        const { onSubmit, error } = useCreation();

        await onSubmit({});

        expect(error.value).toBe("Failed to verify configuration: test request failed");
        expect(createRequests).not.toHaveBeenCalled();
    });

    it("reports the plugin's own message when the configuration test fails", async () => {
        const createRequests = mockCreationTestAndTrackRequests("not_ok");
        const { onSubmit, error, testResults } = useCreation();

        await onSubmit({});

        expect(error.value).toBe("could not connect");
        expect(testResults.value).toEqual(FAILED_CONNECTION_STATUS);
        expect(createRequests).not.toHaveBeenCalled();
    });
});
