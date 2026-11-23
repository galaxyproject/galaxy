import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import { fetchDatatypeConverters } from "./datatypes";

const { server, http } = useServerMock();

describe("fetchDatatypeConverters", () => {
    it("returns the installed converters", async () => {
        const converters = [{ source: "fasta", target: "tabular", tool_id: "CONVERTER_fasta_to_tabular" }];
        server.use(http.get("/api/datatypes/converters", ({ response }) => response(200).json(converters)));

        expect(await fetchDatatypeConverters()).toEqual(converters);
    });

    it("throws the error message on failure", async () => {
        server.use(
            http.get("/api/datatypes/converters", ({ response }) =>
                response("5XX").json({ err_msg: "Registry unavailable", err_code: 500 }, { status: 500 }),
            ),
        );

        await expect(fetchDatatypeConverters()).rejects.toThrow("Registry unavailable");
    });
});
