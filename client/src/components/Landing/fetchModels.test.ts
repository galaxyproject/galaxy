import { describe, expect, it } from "vitest";

import type { AnyFetchTarget, NestedElementItem, UrlDataElement } from "@/api/tools";

import type { ParsedFetchWorkbookColumnType } from "../Collections/wizard/types";
import {
    type CellValueType,
    DerivedColumn,
    type FetchTable,
    fetchTargetToRows,
    fetchTargetToTable,
    tableToRequest,
} from "./fetchModels";

// Generated fetch types require backend-defaulted fields that these fixtures intentionally omit.
// The canonical URL/nested factories add those defaults, changing the omission/round-trip inputs.

function sortTagsDeep<T>(value: T): T {
    const result = structuredClone(value);
    function sortTags(node: unknown): void {
        if (Array.isArray(node)) {
            node.forEach(sortTags);
        } else if (node && typeof node === "object") {
            for (const [key, item] of Object.entries(node)) {
                if (key === "tags" && Array.isArray(item)) {
                    item.sort();
                } else {
                    sortTags(item);
                }
            }
        }
    }
    sortTags(result);
    return result;
}

describe("fetchModels", () => {
    const urlDataElement: UrlDataElement = {
        src: "url",
        name: "file1.txt",
        url: "http://example.com/file1.txt",
        MD5: "md5hash",
        dbkey: "?",
        "SHA-1": "sha1hash",
        "SHA-256": "sha256hash",
        "SHA-512": "sha512hash",
        ext: "txt",
        tags: ["name:file1", "group:treatment:control", "foobar"],
    } as UrlDataElement;

    function expectRowToHaveColumnValue(
        table: FetchTable,
        rowIndex: number,
        columnType: ParsedFetchWorkbookColumnType,
        expectedValue: CellValueType,
    ) {
        const columnKey = new DerivedColumn(columnType, 0, "").key();
        const row = table.rows[rowIndex];
        expect(row).toBeDefined();
        expect(row?.[columnKey]).toEqual(expectedValue);
    }

    const simpleTarget: AnyFetchTarget = {
        destination: { type: "hdas" },
        elements: [urlDataElement],
        auto_decompress: false,
    };

    it("fetchTargetToTable returns correct columns and rows for simple target", () => {
        const table = fetchTargetToTable(simpleTarget);
        const columnTypes = table.columns.map((c) => c.type);
        expect(columnTypes).toEqual(
            expect.arrayContaining([
                "name",
                "url",
                "hash_md5",
                "hash_sha1",
                "hash_sha256",
                "hash_sha512",
                "file_type",
                "dbkey",
                "name_tag",
                "group_tags",
                "tags",
            ]),
        );
        expectRowToHaveColumnValue(table, 0, "name", "file1.txt");
        expectRowToHaveColumnValue(table, 0, "url", "http://example.com/file1.txt");
        expectRowToHaveColumnValue(table, 0, "hash_md5", "md5hash");
        expectRowToHaveColumnValue(table, 0, "hash_sha1", "sha1hash");
        expectRowToHaveColumnValue(table, 0, "hash_sha256", "sha256hash");
        expectRowToHaveColumnValue(table, 0, "hash_sha512", "sha512hash");
        expectRowToHaveColumnValue(table, 0, "file_type", "txt");
        expectRowToHaveColumnValue(table, 0, "dbkey", "?");
        expectRowToHaveColumnValue(table, 0, "name_tag", "file1");
        expectRowToHaveColumnValue(table, 0, "group_tags", "treatment:control");
        expectRowToHaveColumnValue(table, 0, "tags", "foobar");
    });

    it("fetchTargetToRows handles missing optional fields", () => {
        const partialElement: UrlDataElement = {
            src: "url",
            name: "file2.txt",
            url: "http://example.com/file2.txt",
        } as UrlDataElement;
        const columns: DerivedColumn[] = [
            new DerivedColumn("name", 0, "Name"),
            new DerivedColumn("url", 0, "URL"),
            new DerivedColumn("hash_md5", 0, "MD5"),
        ];
        const rows = fetchTargetToRows(
            { collection_type: null, elements: [partialElement] } as AnyFetchTarget,
            columns,
            [],
        );
        expect(rows[0]!["name"]).toEqual("file2.txt");
        expect(rows[0]!["url"]).toEqual("http://example.com/file2.txt");
        expect(rows[0]!["hash_md5"]).toEqual(null);
    });

    it("fetchTargetToTable handles collection_type list", () => {
        const partialElement: UrlDataElement = {
            src: "url",
            name: "A",
            url: "http://example.com/file2.txt",
        } as UrlDataElement;
        const target: AnyFetchTarget = {
            destination: { type: "hdas" },
            collection_type: "list",
            elements: [partialElement],
            auto_decompress: false,
        };
        const table = fetchTargetToTable(target);
        const listIdentifierColKey = "list_identifiers";
        // Should include the identifier value in rows
        const identifierRow = table.rows.find((row) => row[listIdentifierColKey] === "A");
        expect(identifierRow).toBeDefined();
    });

    it("fetchTargetToTable throws on unsupported collection_type", () => {
        const target: AnyFetchTarget = {
            collection_type: "foo",
            elements: [],
            destination: { type: "hdas" },
            auto_decompress: false,
        };
        expect(() => fetchTargetToTable(target)).toThrow(/Unsupported collection type part/);
    });

    it("fetchTargetToRows throws if url is missing", () => {
        const badElement: UrlDataElement = {
            src: "url",
            name: "badfile",
            // url missing
        } as UrlDataElement;
        const columns: DerivedColumn[] = [new DerivedColumn("url", 0, "URL")];
        expect(() =>
            fetchTargetToRows({ collection_type: null, elements: [badElement] } as AnyFetchTarget, columns, []),
        ).toThrow(/URL is required/);
    });

    it("fetchTargetToTable handles nested paired collection", () => {
        const forwardElement: UrlDataElement = {
            src: "url",
            name: "forward",
            url: "http://example.com/sample1-forward1.txt",
        } as UrlDataElement;
        const reverseElement: UrlDataElement = {
            src: "url",
            name: "reverse",
            url: "http://example.com/sample1-reverse1.txt",
        } as UrlDataElement;

        const target: AnyFetchTarget = {
            collection_type: "list:paired",
            elements: [
                {
                    name: "sample1",
                    elements: [forwardElement, reverseElement],
                } as NestedElementItem,
            ],
            destination: { type: "hdca" },
            auto_decompress: false,
        };
        const table = fetchTargetToTable(target);
        // Should include left/right in rows
        expect(table.rows.some((row) => row["paired_identifier"] === "forward")).toBe(true);
        expect(table.rows.some((row) => row["paired_identifier"] === "reverse")).toBe(true);
    });

    describe("tableToRequest", () => {
        const simplestUrlElement: UrlDataElement = {
            src: "url",
            url: "http://example.com/file1.txt",
        } as UrlDataElement;

        const elementWithTabToSpace: UrlDataElement = {
            src: "url",
            url: "http://example.com/file2.txt",
            space_to_tab: true,
        } as UrlDataElement;

        const simplestTarget: AnyFetchTarget = {
            destination: { type: "hdas" },
            elements: [simplestUrlElement],
            auto_decompress: false,
        };

        const targetWithDecompressOn: AnyFetchTarget = {
            destination: { type: "hdas" },
            elements: [simplestUrlElement],
            auto_decompress: true,
        };

        const targetWithNoDecompressSpecified: AnyFetchTarget = {
            destination: { type: "hdas" },
            elements: [simplestUrlElement],
        } as AnyFetchTarget;

        const targetWithTabToSpaceElement: AnyFetchTarget = {
            destination: { type: "hdas" },
            elements: [elementWithTabToSpace],
            auto_decompress: false,
        };

        const targetsForRoundTripCheck: AnyFetchTarget[] = [
            simplestTarget,
            simpleTarget,
            targetWithDecompressOn,
            targetWithTabToSpaceElement,
            targetWithNoDecompressSpecified,
        ];

        it("should round trip any supported target", () => {
            targetsForRoundTripCheck.forEach((target) => {
                // Tag order between name/group/plain tags is not preserved by conversion.
                const table = fetchTargetToTable(sortTagsDeep(target));
                const restoredTarget = tableToRequest(table);
                expect(sortTagsDeep(restoredTarget)).toEqual(sortTagsDeep(target));
            });
        });
    });
});
