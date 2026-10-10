import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import testInteractiveToolsResponse from "../components/InteractiveTools/testData/testInteractiveToolsResponse";
import { sseMockFactory } from "./_testing/sseStoreSupport";
import { useEntryPointStore } from "./entryPointStore";
import { setupTestPinia } from "./testUtils";

// Data-method tests do not open an EventSource; reuse the stores’ SSE mock.
const sseState = vi.hoisted(() => ({
    onEvent: null,
    connect: vi.fn(),
    disconnect: vi.fn(),
    connected: null,
}));
vi.mock("@/composables/useNotificationSSE", () => sseMockFactory(sseState));

const { server, http } = useServerMock();

describe("stores/EntryPointStore", () => {
    let store;

    beforeEach(async () => {
        server.use(
            http.untyped.get("/api/entry_points", ({ request }) => {
                expect(new URL(request.url).searchParams.get("running")).toBe("true");
                return HttpResponse.json(testInteractiveToolsResponse);
            }),
        );
        setupTestPinia();
        store = useEntryPointStore();
        await store.fetchEntryPoints();
    });

    it("merges a partial update and removes entry points omitted from the response", () => {
        const updateData = [
            {
                model_class: "InteractiveToolEntryPoint",
                id: "b887d74393f85b6d",
                job_id: "52e496b945151ee8",
                name: "Oh there you go, bringing class into it again.",
                created_time: "2020-01-24T15:59:22.406480",
                modified_time: "2020-02-24T15:59:24.757453",
                output_datasets_ids: ["4e9e0c7225b0bb81"],
                target: "http://b887d74393f85b6d-b1fd3f42331a49c1b3d8a4d1b27240b8.interactivetoolentrypoint.interactivetool.localhost:8080/loginapikey/oleg",
            },
        ];
        store.updateEntryPoints(updateData);
        expect(store.entryPoints).toHaveLength(1);
        expect(store.entryPoints[0].name).toBe("Oh there you go, bringing class into it again.");
        expect(store.entryPoints[0].active).toBe(true);
    });
    it("removes the matching entry point while retaining the other entry point", () => {
        expect(store.entryPoints.map(({ id }) => id)).toEqual(["52e496b945151ee8", "b887d74393f85b6d"]);
        store.removeEntryPoint("52e496b945151ee8");
        expect(store.entryPoints.map(({ id }) => id)).toEqual(["b887d74393f85b6d"]);
    });
    it("filters entry points by job ID", () => {
        const entryPointForJob = store.entryPointsForJob("6fc9fbb81c497f69");
        expect(entryPointForJob).toHaveLength(1);
        expect(entryPointForJob[0].id).toBe("52e496b945151ee8");
        expect(entryPointForJob[0].active).toBe(true);
    });
    it("filters entry points by output dataset ID", () => {
        const entryPointForHda = store.entryPointsForHda("4e9e0c7225b0bb81");
        expect(entryPointForHda).toHaveLength(1);
        expect(entryPointForHda[0].id).toBe("52e496b945151ee8");
        expect(entryPointForHda[0].active).toBe(true);
    });
});
