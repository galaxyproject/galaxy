import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import type { ColDef, ValueSetterParams } from "ag-grid-community";
import flushPromises from "flush-promises";
import { HttpResponse } from "msw";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, toRaw } from "vue";

import type { HDCADetailed, SampleSheetColumnDefinitions } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import type { SampleSheetCollectionType } from "@/api/datasetCollections";
import type { InitialElements } from "@/components/Collections/wizard/types";
import { Toast } from "@/composables/toast";

import type { AgRowData } from "./useSampleSheetGrid";
import { parseWorkbook, workbookForCollection } from "./workbooks";

import SampleSheetGrid from "./SampleSheetGrid.vue";

vi.mock("@/composables/toast");

const toastError = vi.mocked(Toast.error);

const localVue = getLocalVue(true);

// Stub only the grid itself, so the test renders it through useAgGrid's async wrapper like the app does.
vi.mock("ag-grid-vue3", () => ({
    AgGridVue: defineComponent({
        name: "AgGridVue",
        props: {
            modelValue: { type: Array, default: undefined },
            rowData: { type: Array, default: undefined },
            columnDefs: { type: Array, default: undefined },
        },
        emits: ["update:modelValue"],
        render() {
            return h("div");
        },
    }),
}));

const { server, http } = useServerMock();
beforeEach(() => {
    vi.clearAllMocks();
    server.use(
        http.get("/api/configuration", ({ response }) => response(200).json({})),
        http.get("/api/genomes", ({ response }) =>
            response(200).json([
                ["Unspecified", "?"],
                ["Human", "hg38"],
            ]),
        ),
        http.get("/api/datatypes/types_and_mapping", ({ response }) =>
            response(200).json({
                datatypes: [],
                datatypes_mapping: { ext_to_class_name: {}, class_to_classes: {} },
            }),
        ),
        http.get("/api/datatypes", ({ response }) =>
            response(200).json([
                { extension: "fastqsanger", description: "FASTQ", description_url: null, display_in_upload: true },
            ]),
        ),
    );
});

async function mountGrid(
    initialElements: InitialElements,
    columnDefinitions: SampleSheetColumnDefinitions = [],
    collectionType: SampleSheetCollectionType = "sample_sheet",
) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    const wrapper = mount(SampleSheetGrid, {
        props: {
            currentHistoryId: "history-1",
            collectionType,
            columnDefinitions,
            initialElements,
            busy: false,
        },
        global: withPlugins(localVue, pinia),
    });
    await flushPromises();
    return wrapper;
}

type Wrapper = Awaited<ReturnType<typeof mountGrid>>;

function grid(wrapper: Wrapper) {
    return wrapper.findComponent({ name: "AgGridVue" });
}

function gridRows(wrapper: Wrapper): AgRowData[] {
    const props = grid(wrapper).props() as { modelValue?: AgRowData[]; rowData?: AgRowData[] };
    return props.modelValue ?? props.rowData ?? [];
}

function gridColumn(wrapper: Wrapper, field: string): ColDef {
    const columns = grid(wrapper).props("columnDefs") as ColDef[];
    const column = columns.find((col) => col.field === field);
    expect(column).toBeDefined();
    return column!;
}

/** Run a column's `valueSetter` the way the grid does after an edit of `rowIndex`; the grid holds raw rows. */
function setCell(column: ColDef, rows: AgRowData[], rowIndex: number, newValue: unknown): boolean {
    const params = {
        newValue,
        data: toRaw(rows[rowIndex]),
        node: { rowIndex },
        colDef: column,
        api: {
            refreshCells: vi.fn(),
            forEachNode: (callback: (node: { rowIndex: number; data: AgRowData }) => void) =>
                rows.forEach((data, index) => callback({ rowIndex: index, data: toRaw(data) })),
        },
    } as unknown as ValueSetterParams;
    if (typeof column.valueSetter === "function") {
        return column.valueSetter(params);
    }
    params.data[column.field!] = newValue;
    return true;
}

const URIS: InitialElements = [
    ["https://example.org/a.fastq", "a"],
    ["https://example.org/b.fastq", "b"],
];

describe("SampleSheetGrid", () => {
    it("rebuilds its rows when the initial elements change", async () => {
        const wrapper = await mountGrid([["https://example.org/a.fastq", "a"]]);
        expect(gridRows(wrapper).map((row) => row.list_identifiers)).toEqual(["a"]);

        await wrapper.setProps({ initialElements: URIS });
        await flushPromises();

        expect(gridRows(wrapper).map((row) => row.list_identifiers)).toEqual(["a", "b"]);
    });

    it("rejects an element identifier another row already uses", async () => {
        const wrapper = await mountGrid(URIS);
        const rows = gridRows(wrapper);

        expect(setCell(gridColumn(wrapper, "list_identifiers"), rows, 0, "b")).toBe(false);

        expect(rows[0]!.list_identifiers).toBe("a");
        expect(toastError).toHaveBeenCalled();
    });

    it("accepts the booleans the grid's checkbox editor produces", async () => {
        const wrapper = await mountGrid(URIS, [{ name: "control", type: "boolean", optional: false }]);
        const rows = gridRows(wrapper);

        expect(setCell(gridColumn(wrapper, "control"), rows, 0, true)).toBe(true);

        expect(rows[0]!.control).toBe(true);
    });

    it("rejects clearing a required integer and keeps the old value", async () => {
        const wrapper = await mountGrid(URIS, [{ name: "replicate", type: "int", optional: false }]);
        const rows = gridRows(wrapper);

        // The number editor the grid infers from the starting 0 hands over null when cleared.
        expect(setCell(gridColumn(wrapper, "replicate"), rows, 0, null)).toBe(false);

        expect(rows[0]!.replicate).toBe(0);
        expect(toastError).toHaveBeenCalledWith('Invalid value for column "replicate".');
    });

    it("reports a rejected float edit and keeps the old value", async () => {
        const wrapper = await mountGrid(URIS, [{ name: "dose", type: "float", optional: false }]);
        const rows = gridRows(wrapper);

        expect(setCell(gridColumn(wrapper, "dose"), rows, 0, "1abc")).toBe(false);
        expect(rows[0]!.dose).toBe(0);
        expect(toastError).toHaveBeenCalledWith('Invalid value for column "dose".');
    });

    it.each([
        ["file_type", "fastqsanger", "auto", "Unknown file extension: missing."],
        ["dbkey", "hg38", "?", "Unknown dbkey: missing."],
    ])("validates workbook %s edits and preserves empty-cell fallback", async (field, value, defaultValue, message) => {
        const wrapper = await mountGrid({
            rows: [{ url: "https://example.org/a.fq", list_identifiers: "a", [field]: value }],
            extra_columns: [{ title: field, type: field }],
            parse_log: [],
        } as unknown as InitialElements);
        const rows = gridRows(wrapper);
        const column = gridColumn(wrapper, field);

        expect(setCell(column, rows, 0, "missing")).toBe(false);
        expect(rows[0]![field]).toBe(value);
        expect(toastError).toHaveBeenCalledWith(message);
        toastError.mockClear();

        expect(setCell(column, rows, 0, defaultValue)).toBe(true);
        expect(rows[0]![field]).toBe(defaultValue);
        expect(setCell(column, rows, 0, value)).toBe(true);
        expect(rows[0]![field]).toBe(value);
        expect(setCell(column, rows, 0, "")).toBe(true);
        expect(rows[0]![field]).toBe("");
        expect(setCell(column, rows, 0, null)).toBe(true);
        expect(rows[0]![field]).toBe("");
        expect(toastError).not.toHaveBeenCalled();

        (wrapper.vm as unknown as { attemptCreate: () => void }).attemptCreate();
        const target = wrapper.emitted("on-fetch-target")![0]![0] as { elements: Record<string, unknown>[] };
        expect(target.elements[0]![field === "file_type" ? "ext" : "dbkey"]).toBe(defaultValue);
    });

    it("offers renamed element identifiers in element_identifier columns", async () => {
        const wrapper = await mountGrid(URIS, [
            { name: "control_sample", type: "element_identifier", optional: false },
        ]);
        const column = gridColumn(wrapper, "control_sample");
        const editorValues = () => (column.cellEditorParams as () => { values: string[] })().values;
        expect(editorValues()).toEqual(["a", "b"]);

        // The grid writes edits into its raw row objects, then emits them through v-model.
        const rows = gridRows(wrapper).map((row) => toRaw(row));
        rows[1]!.list_identifiers = "renamed";
        grid(wrapper).vm.$emit("update:modelValue", Object.freeze(rows));
        await flushPromises();

        expect(editorValues()).toEqual(["a", "renamed"]);
    });

    it("updates references in other rows and self references when renaming, but keeps them on a rejected rename", async () => {
        const wrapper = await mountGrid(URIS, [{ name: "reference", type: "element_identifier", optional: true }]);
        const rows = gridRows(wrapper);
        const reference = gridColumn(wrapper, "reference");
        setCell(reference, rows, 0, "a");
        setCell(reference, rows, 1, "a");
        const identifier = gridColumn(wrapper, "list_identifiers");
        expect(setCell(identifier, rows, 0, "b")).toBe(false);
        expect(rows.map((row) => row.reference)).toEqual(["a", "a"]);
        expect(setCell(identifier, rows, 0, "renamed")).toBe(true);
        expect(rows.map((row) => row.reference)).toEqual(["renamed", "renamed"]);
        (wrapper.vm as unknown as { attemptCreate: () => void }).attemptCreate();
        expect(wrapper.emitted("on-fetch-target")![0]![0]).toMatchObject({
            elements: [
                { name: "renamed", row: ["renamed"] },
                { name: "b", row: ["renamed"] },
            ],
        });
    });

    it("rejects a rename that violates a referencing column's restrictions", async () => {
        const wrapper = await mountGrid(URIS, [
            { name: "reference", type: "element_identifier", optional: true, restrictions: ["a", "b"] },
        ]);
        const rows = gridRows(wrapper);
        expect(setCell(gridColumn(wrapper, "reference"), rows, 1, "a")).toBe(true);
        expect(setCell(gridColumn(wrapper, "list_identifiers"), rows, 0, "renamed")).toBe(false);
        expect(rows[0]!.list_identifiers).toBe("a");
        expect(rows[1]!.reference).toBe("a");
        expect(toastError).toHaveBeenCalledWith(
            "Cannot rename this identifier because a referencing column does not allow the new value.",
        );
        (wrapper.vm as unknown as { attemptCreate: () => void }).attemptCreate();
        expect(wrapper.emitted("on-fetch-target")![0]![0]).toMatchObject({
            elements: [
                { name: "a", row: [""] },
                { name: "b", row: ["a"] },
            ],
        });
    });

    it.each(["int", "string"] as const)(
        "clears an existing optional restricted %s value in the payload",
        async (type) => {
            const value = type === "int" ? 1 : "treated";
            const wrapper = await mountGrid(URIS, [{ name: "condition", type, optional: true, restrictions: [value] }]);
            const rows = gridRows(wrapper);
            const column = gridColumn(wrapper, "condition");
            expect(setCell(column, rows, 0, value)).toBe(true);
            expect(setCell(column, rows, 0, "")).toBe(true);
            expect(rows[0]!.condition).toBeNull();
            if (type === "string") {
                expect(column.cellEditorParams).toEqual({ values: ["", value] });
            }
            (wrapper.vm as unknown as { attemptCreate: () => void }).attemptCreate();
            expect(wrapper.emitted("on-fetch-target")![0]![0]).toMatchObject({
                elements: [
                    { name: "a", row: [null] },
                    { name: "b", row: [type === "int" ? null : ""] },
                ],
            });
        },
    );

    it("imports a URI sheet with a metadata column named __model_object", async () => {
        const wrapper = await mountGrid(URIS, [{ name: "__model_object", type: "string", optional: false }]);
        const rows = gridRows(wrapper);
        expect(setCell(gridColumn(wrapper, "__model_object"), rows, 0, "treated")).toBe(true);
        (wrapper.vm as unknown as { attemptCreate: () => void }).attemptCreate();
        expect(wrapper.emitted("on-fetch-target")![0]![0]).toMatchObject({
            elements: [
                { name: "a", url: "https://example.org/a.fastq", row: ["treated"] },
                { name: "b", url: "https://example.org/b.fastq", row: [""] },
            ],
        });
    });

    it.each(["sample_sheet", "sample_sheet:paired"] as const)(
        "reloads a downloaded %s collection workbook and submits its edited metadata",
        async (collectionType) => {
            const paired = collectionType === "sample_sheet:paired";
            const object = paired
                ? {
                      model_class: "DatasetCollection",
                      collection_type: "paired",
                      elements: [
                          { element_identifier: "forward", object: { id: "hda1" } },
                          { element_identifier: "reverse", object: { id: "hda2" } },
                      ],
                  }
                : { model_class: "HistoryDatasetAssociation", id: "hda1" };
            const collection = {
                id: "hdca1",
                name: "source",
                elements: [
                    { element_identifier: "a", object },
                    { element_identifier: "b", object: { ...object, id: "hda3" } },
                ],
            } as unknown as HDCADetailed;
            const columns = [
                { name: "__model_object", type: "string", optional: false },
            ] as SampleSheetColumnDefinitions;
            const wrapper = await mountGrid(collection, columns, collectionType);
            const download = vi.fn();
            const createObjectURL = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:workbook");
            const revokeObjectURL = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
            const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
            server.use(
                http.post("/api/dataset_collections/{hdca_id}/sample_sheet_workbook", async ({ request, params }) => {
                    download((params as { hdca_id: string }).hdca_id, await request.json());
                    return new HttpResponse<never>(null);
                }),
                http.post("/api/sample_sheet_workbook/parse", async ({ request, response }) => {
                    expect(await request.json()).toMatchObject({
                        prefix_columns_type: "ModelObjects",
                        content: "edited-workbook",
                    });
                    return response(200).json({
                        rows: [
                            { list_identifiers: "b", __model_object: "control" },
                            { list_identifiers: "a", __model_object: "treated" },
                        ],
                        extra_columns: [],
                        parse_log: [],
                    });
                }),
            );
            try {
                await wrapper.find(".below-grid-link a").trigger("click");
                await flushPromises();
                expect(download).toHaveBeenCalledWith("hdca1", { column_definitions: columns });
                const { data } = await parseWorkbook(collectionType, columns, "ModelObjects", "edited-workbook");
                expect(data).toBeDefined();
                await wrapper.setProps({ initialElements: workbookForCollection(data!, collection) });
                await flushPromises();
                expect((grid(wrapper).props("columnDefs") as ColDef[]).some((column) => column.field === "url")).toBe(
                    false,
                );
                expect(setCell(gridColumn(wrapper, "__model_object"), gridRows(wrapper), 1, "edited")).toBe(true);
                (wrapper.vm as unknown as { attemptCreate: () => void }).attemptCreate();
                expect(wrapper.emitted("on-fetch-target")).toBeUndefined();
                const payload = wrapper.emitted("on-collection-create-payload")![0]![0];
                expect(payload).toMatchObject({
                    collection_type: collectionType,
                    rows: { b: ["control"], a: ["edited"] },
                });
                expect(payload).toMatchObject({
                    element_identifiers: paired
                        ? [
                              {
                                  name: "b",
                                  src: "new_collection",
                                  element_identifiers: [
                                      { name: "forward", src: "hda", id: "hda1" },
                                      { name: "reverse", src: "hda", id: "hda2" },
                                  ],
                              },
                              {
                                  name: "a",
                                  src: "new_collection",
                                  element_identifiers: [
                                      { name: "forward", src: "hda", id: "hda1" },
                                      { name: "reverse", src: "hda", id: "hda2" },
                                  ],
                              },
                          ]
                        : [
                              { name: "b", src: "hda", id: "hda3" },
                              { name: "a", src: "hda", id: "hda1" },
                          ],
                });
                const badWorkbook = { ...data!, rows: [{ list_identifiers: "missing" }] };
                expect(() => workbookForCollection(badWorkbook, collection)).toThrow("Unknown or duplicate");
                expect(() =>
                    workbookForCollection({ ...data!, rows: [data!.rows[0]!, data!.rows[0]!] }, collection),
                ).toThrow("Unknown or duplicate");
            } finally {
                createObjectURL.mockRestore();
                revokeObjectURL.mockRestore();
                click.mockRestore();
                wrapper.unmount();
            }
        },
    );

    describe("create payloads", () => {
        async function fetchTarget(wrapper: Wrapper) {
            (wrapper.vm as unknown as { attemptCreate: () => void }).attemptCreate();
            await flushPromises();
            return wrapper.emitted("on-fetch-target")![0]![0] as { elements: object[] };
        }

        it("fetches one URL element per row of a sample sheet", async () => {
            const wrapper = await mountGrid(
                [["https://example.org/a.fastq", "a"]],
                [{ name: "replicate", type: "int", optional: false }],
            );

            expect(await fetchTarget(wrapper)).toMatchObject({
                destination: { type: "hdca" },
                collection_type: "sample_sheet",
                name: "Sample Sheet for Workflow Input",
                elements: [{ src: "url", url: "https://example.org/a.fastq", name: "a", ext: "auto", row: [0] }],
            });
        });

        it("applies workbook metadata to the forward or reverse URL its column names", async () => {
            const workbook = {
                rows: [
                    { url: "https://example.org/a_1.fq", url_1: "https://example.org/a_2.fq", list_identifiers: "a" },
                ].map((row) => ({ ...row, replicate: 2, hash_md5: "abc", file_type: "fastqsanger" })),
                extra_columns: [
                    { title: "MD5", type: "hash_md5", type_index: 1 },
                    { title: "Type", type: "file_type", type_index: 0 },
                ],
                parse_log: [],
            } as unknown as InitialElements;
            const wrapper = await mountGrid(
                workbook,
                [{ name: "replicate", type: "int", optional: false }],
                "sample_sheet:paired",
            );

            const [element] = (await fetchTarget(wrapper)).elements as { elements: Record<string, unknown>[] }[];
            expect(element).toMatchObject({ name: "a", row: [2] });
            const [forward, reverse] = element!.elements;
            expect(forward).toMatchObject({ name: "forward", url: "https://example.org/a_1.fq", ext: "fastqsanger" });
            expect(forward!.MD5).toBeUndefined();
            expect(reverse).toMatchObject({ name: "reverse", url: "https://example.org/a_2.fq", MD5: "abc" });
        });

        it("fetches a lone URL of a paired_or_unpaired sheet as unpaired", async () => {
            const wrapper = await mountGrid(
                [["https://example.org/a.fq", "", "a"]],
                [],
                "sample_sheet:paired_or_unpaired",
            );

            expect(await fetchTarget(wrapper)).toMatchObject({
                elements: [{ name: "a", elements: [{ name: "unpaired", url: "https://example.org/a.fq" }] }],
            });
        });

        it("builds a paired sample sheet from existing collection pairs", async () => {
            const collection = {
                id: "hdca1",
                name: "my pairs",
                elements: [
                    {
                        element_identifier: "pair1",
                        object: {
                            model_class: "DatasetCollection",
                            collection_type: "paired",
                            elements: [
                                { element_identifier: "forward", object: { id: "hda1" } },
                                { element_identifier: "reverse", object: { id: "hda2" } },
                            ],
                        },
                    },
                ],
            } as unknown as InitialElements;
            const wrapper = await mountGrid(collection, [], "sample_sheet:paired");

            (wrapper.vm as unknown as { attemptCreate: () => void }).attemptCreate();
            await flushPromises();

            expect(wrapper.emitted("on-collection-create-payload")![0]![0]).toMatchObject({
                collection_type: "sample_sheet:paired",
                element_identifiers: [
                    {
                        name: "pair1",
                        src: "new_collection",
                        collection_type: "paired",
                        element_identifiers: [
                            { name: "forward", src: "hda", id: "hda1" },
                            { name: "reverse", src: "hda", id: "hda2" },
                        ],
                    },
                ],
                rows: { pair1: [] },
            });
        });

        it("builds a sample sheet from an existing collection's datasets", async () => {
            const collection = {
                id: "hdca1",
                name: "my list",
                elements: [{ element_identifier: "e1", object: { id: "hda1" } }],
            } as unknown as InitialElements;
            const wrapper = await mountGrid(collection, [{ name: "condition", type: "string", optional: false }]);

            (wrapper.vm as unknown as { attemptCreate: () => void }).attemptCreate();
            await flushPromises();

            expect(wrapper.emitted("on-collection-create-payload")![0]![0]).toMatchObject({
                name: "my list (as sample sheet)",
                collection_type: "sample_sheet",
                element_identifiers: [{ name: "e1", src: "hda", id: "hda1" }],
                rows: { e1: [""] },
            });
        });
    });
});
