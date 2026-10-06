import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import type { ColDef, ValueSetterParams } from "ag-grid-community";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, toRaw } from "vue";

import type { SampleSheetColumnDefinitions } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import type { SampleSheetCollectionType } from "@/api/datasetCollections";
import type { InitialElements } from "@/components/Collections/wizard/types";
import { Toast } from "@/composables/toast";

import type { AgRowData } from "./useSampleSheetGrid";

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
        http.get("/api/genomes", ({ response }) => response(200).json([])),
        http.get("/api/datatypes", ({ response }) => response(200).json([])),
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
            forEachNode: (callback: (node: { rowIndex: number; data: AgRowData }) => void) =>
                rows.forEach((data, index) => callback({ rowIndex: index, data: toRaw(data) })),
        },
    } as unknown as ValueSetterParams;
    return (column.valueSetter as (params: ValueSetterParams) => boolean)(params);
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

    it.each(["", null])("rejects clearing a required integer to %j", async (cleared) => {
        const wrapper = await mountGrid(URIS, [{ name: "replicate", type: "int", optional: false }]);
        const rows = gridRows(wrapper);

        expect(setCell(gridColumn(wrapper, "replicate"), rows, 0, cleared)).toBe(false);

        expect(rows[0]!.replicate).toBe(0);
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
