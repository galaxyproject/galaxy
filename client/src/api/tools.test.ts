import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import { fetchToolDataInputs, type ToolDataInput } from "./tools";

const { server, http } = useServerMock();

const TABULAR_INPUT: ToolDataInput = {
    name: "infile",
    extensions: ["tabular"],
    multiple: false,
    type: "data",
    collection_type: null,
};

describe("fetchToolDataInputs", () => {
    it("requests the data inputs of one tool type", async () => {
        const toolTypes: (string | null)[] = [];
        server.use(
            http.get("/api/tools/data_inputs", ({ query, response }) => {
                toolTypes.push(query.get("tool_type"));
                return response(200).json({ interactive_tool_tabular: [TABULAR_INPUT] });
            }),
        );

        expect(await fetchToolDataInputs("interactive")).toEqual({ interactive_tool_tabular: [TABULAR_INPUT] });
        expect(toolTypes).toEqual(["interactive"]);
    });

    it("throws the error message on failure", async () => {
        server.use(
            http.get("/api/tools/data_inputs", ({ response }) =>
                response("5XX").json({ err_msg: "Toolbox unavailable", err_code: 500 }, { status: 500 }),
            ),
        );

        await expect(fetchToolDataInputs()).rejects.toThrow("Toolbox unavailable");
    });
});
