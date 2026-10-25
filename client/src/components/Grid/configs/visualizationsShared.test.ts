import { afterEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import type { Operation } from "./types";
import gridConfig from "./visualizationsShared";

const { server, http } = useServerMock();

function removeOperation(): Operation | undefined {
    const titleField = gridConfig.fields.find((field) => field.key === "title");
    return titleField?.operations?.find((operation) => operation.title === "Remove from Shared");
}

describe("visualizationsShared grid", () => {
    it("removes the current user's share of a visualization", async () => {
        const unshared: string[] = [];
        server.use(
            http.put("/api/visualizations/{id}/unshare_with_me", ({ params, response }) => {
                unshared.push(params.id);
                return response(204).empty();
            }),
        );

        const result = await removeOperation()?.handler({ id: "viz_id", title: "Shared Viz" });

        expect(unshared).toEqual(["viz_id"]);
        expect(result).toEqual({
            status: "success",
            message: "'Shared Viz' has been removed from your shared visualizations.",
        });
    });

    it("reports a failed removal", async () => {
        server.use(
            http.put("/api/visualizations/{id}/unshare_with_me", ({ response }) => {
                return response("4XX").json({ err_msg: "Visualization not found", err_code: 404 }, { status: 404 });
            }),
        );

        const result = await removeOperation()?.handler({ id: "viz_id", title: "Shared Viz" });

        expect(result).toEqual({
            status: "danger",
            message: "Failed to remove 'Shared Viz': Visualization not found.",
        });
    });
});

describe("visualizationsShared grid batch", () => {
    const ROWS = [
        { id: "viz_1", title: "First Viz" },
        { id: "viz_2", title: "Second Viz" },
    ];

    function batchRemove() {
        return gridConfig.batch?.find((operation) => operation.title === "Remove from Shared");
    }

    function interceptUnshare(failId?: string) {
        const unshared: string[] = [];
        server.use(
            http.put("/api/visualizations/{id}/unshare_with_me", ({ params, response }) => {
                unshared.push(params.id);
                if (params.id === failId) {
                    return response("4XX").json({ err_msg: "Visualization not found", err_code: 404 }, { status: 404 });
                }
                return response(204).empty();
            }),
        );
        return unshared;
    }

    function stubConfirm(answer: boolean) {
        const confirm = vi.fn(() => answer);
        vi.stubGlobal("confirm", confirm);
        return confirm;
    }

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it("removes every selected share once confirmed", async () => {
        const unshared = interceptUnshare();
        const confirm = stubConfirm(true);

        const result = await batchRemove()?.handler(ROWS);

        expect(confirm).toHaveBeenCalledTimes(1);
        expect(unshared).toEqual(["viz_1", "viz_2"]);
        expect(result).toEqual({
            status: "success",
            message: "Removed 2 visualizations from your shared visualizations.",
        });
    });

    it("keeps every share when removal is not confirmed", async () => {
        const unshared = interceptUnshare();
        const confirm = stubConfirm(false);

        expect(batchRemove()).toBeDefined();
        const result = await batchRemove()?.handler(ROWS);

        expect(confirm).toHaveBeenCalledTimes(1);
        expect(unshared).toEqual([]);
        expect(result).toBeUndefined();
    });

    it("reports the visualizations whose share could not be removed", async () => {
        const unshared = interceptUnshare("viz_2");
        stubConfirm(true);

        const result = await batchRemove()?.handler(ROWS);

        expect(unshared).toEqual(["viz_1", "viz_2"]);
        expect(result).toEqual({
            status: "danger",
            message: "Removed 1 of 2 visualizations. Failed to remove 'Second Viz' (Visualization not found).",
        });
    });
});
