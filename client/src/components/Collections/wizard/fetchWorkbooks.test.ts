import { forBuilder } from "./fetchWorkbooks";
import type { ParsedFetchWorkbook } from "./types";

describe("forBuilder", () => {
    it("should return the correct ForBuilderResponse for a valid ParsedFetchWorkbook", () => {
        const parsedWorkbook: ParsedFetchWorkbook = {
            rows: [
                { list_identifiers: "Row1", url: "http://example.com/1", dbkey: "db1" },
                { list_identifiers: "Row2", url: "http://example.com/2", dbkey: "db2" },
            ],
            columns: [
                { type: "list_identifiers", title: "Name", type_index: 0 },
                { type: "url", title: "URI", type_index: 0 },
                { type: "dbkey", title: "Genome", type_index: 0 },
            ],
            workbook_type: "datasets",
            parse_log: [],
        };

        const result = forBuilder(parsedWorkbook);

        expect(result.initialElements).toEqual([
            ["Row1", "http://example.com/1", "db1"],
            ["Row2", "http://example.com/2", "db2"],
        ]);
        expect(result.rulesCreatingWhat).toBe("datasets");
        expect(result.initialMapping).toEqual([
            { type: "list_identifiers", columns: [0] },
            { type: "url", columns: [1] },
            { type: "dbkey", columns: [2] },
        ]);
    });
});
