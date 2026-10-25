import { describe, expect, it } from "vitest";

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
