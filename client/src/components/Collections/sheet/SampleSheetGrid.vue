<script lang="ts" setup>
import { faDownload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import type { ColDef, ValueSetterParams } from "ag-grid-community";
import { BCol, BInputGroup, BLink, BRow } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type {
    CollectionElementIdentifiers,
    components,
    CreateNewCollectionPayload,
    DCESummary,
    DCObject,
    HDAObject,
    SampleSheetColumnDefinition,
    SampleSheetColumnDefinitions,
} from "@/api";
import type { SampleSheetCollectionType, SampleSheetColumnValueT } from "@/api/datasetCollections";
import {
    type HdcaUploadTarget,
    type NestedElement,
    nestedElement,
    type UrlDataElement,
    urlDataElement,
} from "@/api/tools";
import { useCollectionCreation } from "@/components/Collections/common/useCollectionCreation";
import { useWorkbookDropHandling } from "@/components/Collections/common/useWorkbooks";
import {
    downloadWorkbook,
    downloadWorkbookForCollection,
    initialValue,
} from "@/components/Collections/sheet/workbooks";
import type { InitialElements, ParsedFetchWorkbookColumn } from "@/components/Collections/wizard/types";
import { Toast } from "@/composables/toast";
import { useUploadConfigurations } from "@/composables/uploadConfigurations";
import { useAgGrid } from "@/composables/useAgGrid";
import localize from "@/utils/localization";

import UploadSelect from "@/components/Upload//UploadSelect.vue";
import UploadSelectExtension from "@/components/Upload/UploadSelectExtension.vue";

type AgRowData = Record<string, unknown>;

interface Props {
    currentHistoryId: string;
    collectionType: SampleSheetCollectionType;
    columnDefinitions: SampleSheetColumnDefinitions;
    initialElements: InitialElements;
    busy: boolean;
    extensions?: string[] | undefined;
}

const props = withDefaults(defineProps<Props>(), {
    columnDefinitions: null,
    extensions: undefined,
});

// Upload properties
const { effectiveExtensions, listDbKeys } = useUploadConfigurations(props.extensions);
const extension = ref("auto");
const dbKey = ref("?");
const listExtensions = computed(() => effectiveExtensions.value.filter((ext) => !ext.composite_files));

const mode = computed<"uris" | "model_objects">(() => {
    if ("elements" in props.initialElements) {
        return "model_objects";
    } else {
        return "uris";
    }
});

const showDbKey = computed(() => {
    return mode.value === "uris";
});

const showExtension = computed(() => {
    return mode.value === "uris";
});

const extraColumns = ref<ParsedFetchWorkbookColumn[]>([]);

function initializeRowData(rowData: AgRowData[]) {
    const initialElements = props.initialElements;
    if ("rows" in initialElements) {
        for (const parsedRow of initialElements.rows) {
            const row: AgRowData = {};
            for (const key in parsedRow) {
                row[key] = parsedRow[key];
            }
            rowData.push(row);
        }
        extraColumns.value = initialElements.extra_columns || [];
    } else if ("elements" in initialElements) {
        for (const element of initialElements.elements) {
            const row: AgRowData = { __model_object: element };
            (props.columnDefinitions || []).forEach((colDef) => {
                row[colDef.name] = initialValue(colDef);
            });
            rowData.push(row);
        }
    } else {
        for (const initialElement of initialElements) {
            const row: AgRowData = { url: initialElement[0] };
            if (
                props.collectionType === "sample_sheet:paired" ||
                props.collectionType === "sample_sheet:paired_or_unpaired"
            ) {
                row["url_1"] = initialElement[1];
                row["list_identifiers"] = initialElement[2] || "";
            } else if (props.collectionType === "sample_sheet") {
                row["list_identifiers"] = initialElement[1] || "";
            } else {
                throw new Error("Collection type not implemented yet");
            }
            (props.columnDefinitions || []).forEach((colDef) => {
                row[colDef.name] = initialValue(colDef);
            });
            rowData.push(row);
        }
    }
}

// Example Row Data
// const rowData = ref([{ "replicate number": 1, treatment: "treatment1", "is control?": true }]);
const rowData = ref<AgRowData[]>([]);

function initialize() {
    rowData.value.splice(0, rowData.value.length);
    initializeRowData(rowData.value);
}

const { gridApi, AgGridVue, onGridReady, theme } = useAgGrid(resize);

function resize() {
    if (gridApi.value) {
        gridApi.value.sizeColumnsToFit();
    }
}

watch(
    () => {
        props.initialElements;
    },
    () => {
        initialize();
        // is this block needed?
        if (gridApi.value) {
            const params = {
                force: true,
                suppressFlash: true,
            };
            gridApi.value!.refreshCells(params);
        }
    },
    {
        immediate: true,
    }
);

function validate(value: string, columnDefinition: SampleSheetColumnDefinition): boolean {
    if (columnDefinition.restrictions && !columnDefinition.restrictions.includes(value)) {
        return false; // Invalid if not in restrictions
    }
    switch (columnDefinition.type) {
        case "int":
            return Number.isInteger(Number(value));
        case "float":
            return !isNaN(parseFloat(value));
        case "boolean":
            return value.toLowerCase() === "true" || value.toLowerCase() === "false";
        case "string":
        default:
            if (!/^[\w\-_ ?]*$/.test(value)) {
                return false;
            }
            return true;
    }
}

function valueSetter(params: ValueSetterParams, columnDefinition: SampleSheetColumnDefinition): boolean {
    const value = params.newValue;
    if (validate(value, columnDefinition)) {
        params.data[params.colDef.field!] = value;
        return true;
    } else {
        return false;
    }
}

// Generate Column Definitions from Schema
function generateGridColumnDefs(columnDefinitions: SampleSheetColumnDefinitions): ColDef[] {
    const columns: ColDef[] = [];
    if (mode.value === "model_objects") {
        columns.push({
            headerName: "Identifier (Unique Name)",
            field: "__model_object",
            editable: false,
            cellEditorParams: {},
            valueFormatter: (params) => {
                return params.data.__model_object.element_identifier;
            },
        });
    } else {
        const collectionType = props.collectionType;
        if (collectionType === "sample_sheet") {
            columns.push(uriColumn("URI", "url"), elementIdentifierColumn());
        } else if (collectionType === "sample_sheet:paired") {
            columns.push(
                uriColumn("URI 1 (Forward)", "url"),
                uriColumn("URI 2 (Reverse)", "url_1"),
                elementIdentifierColumn()
            );
        } else if (collectionType === "sample_sheet:paired_or_unpaired") {
            columns.push(
                uriColumn("URI 1 (Forward)", "url"),
                uriColumn("URI 2 (Optional/Reverse)", "url_1"),
                elementIdentifierColumn()
            );
        } else {
            throw new Error("Mode not implemented yet");
        }
    }
    (columnDefinitions || []).forEach((colDef) => {
        const headerDescription = colDef.description || colDef.name;
        const hasCustomHeaderDescription = headerDescription != colDef.name;
        let headerClass = "";
        if (hasCustomHeaderDescription) {
            headerClass = "ag-grid-column-has-custom-header-description";
        }
        const baseDef: ColDef = {
            headerName: colDef.name,
            headerTooltip: colDef.description || colDef.name,
            headerClass,
            field: colDef.name,
            editable: true,
            cellEditorParams: {},
            valueSetter: (params) => {
                return valueSetter(params, colDef);
            },
        };

        // Restrictions: Add dropdown editor for string type with restrictions
        if (colDef.restrictions && colDef.type === "string") {
            baseDef.cellEditor = "agSelectCellEditor";
            baseDef.cellEditorParams = {
                values: colDef.restrictions,
            };
        }

        if (colDef.type === "element_identifier") {
            const elementIdentifierOptions = () => {
                if (colDef.optional) {
                    return ["", ...elementIdentifiers.value];
                } else {
                    return elementIdentifiers.value;
                }
            };

            baseDef.cellEditor = "agSelectCellEditor";
            baseDef.cellEditorParams = () => {
                return {
                    values: elementIdentifierOptions(),
                };
            };
        }

        // Validators
        baseDef.cellEditorParams.validate = (value: string) => validate(value, colDef);
        columns.push(baseDef);
    });
    for (const extraColumn of extraColumns.value) {
        const baseDef: ColDef = {
            headerName: extraColumn.title,
            field: extraColumn.type,
            editable: true,
            cellEditorParams: {},
        };
        columns.push(baseDef);
    }
    return columns;
}

function uriColumn(headerTitle: string, name: string): ColDef {
    // dynamic field names so these don't conflict for paired?
    const baseDef: ColDef = {
        headerName: headerTitle,
        field: name,
        editable: false,
        cellEditorParams: {},
    };
    return baseDef;
}

function elementIdentifierColumn(): ColDef {
    const baseDef: ColDef = {
        headerName: "Element identifier",
        field: "list_identifiers",
        editable: true,
        cellEditorParams: {},
        valueSetter: (params) => {
            const newValue = params.newValue;
            const rowIndex = params.node?.rowIndex ?? -1;
            let isDuplicate = false;

            params.api.forEachNode((node) => {
                if (node.rowIndex !== rowIndex && node.data.element_identifier === newValue) {
                    Toast.error("Element identifier values must be unique, supplied value already exists.");
                    isDuplicate = true;
                }
            });

            if (isDuplicate) {
                return false; // Prevent duplicate values
            } else {
                params.data[params.colDef.field!] = newValue;
                return true;
            }
        },
    };
    return baseDef;
}

// Column Definitions
const columnDefs = computed(() => {
    return generateGridColumnDefs(props.columnDefinitions);
});

// Default Column Properties
const defaultColDef = ref<ColDef>({
    editable: true,
    sortable: true,
    filter: true,
    resizable: true,
});

const style = computed(() => {
    return { width: "100%", height: "500px" };
});

const emit = defineEmits<{
    (e: "workbook-contents", base64Content: string): void;
    (e: "on-fetch-target", target: HdcaUploadTarget): void;
    (e: "on-collection-create-payload", payload: CreateNewCollectionPayload): void;
}>();

async function handleWorkbook(base64Content: string) {
    emit("workbook-contents", base64Content);
}

const { handleDrop, isDragging } = useWorkbookDropHandling(handleWorkbook);

const rootClasses = computed(() => {
    const classes: string[] = [theme, "dropzone"];
    if (isDragging.value) {
        classes.push("highlight");
    }
    return classes;
});

const fromWorkbookUpload = computed<Boolean>(() => {
    return "rows" in props.initialElements;
});

function downloadSeededWorkbook() {
    const initialRows = [];
    const initialElements = props.initialElements;
    if ("rows" in initialElements) {
        // link won't appear - don't do anything
    } else if ("elements" in initialElements) {
        const hdca_id = initialElements.id;
        downloadWorkbookForCollection(props.columnDefinitions, hdca_id);
    } else {
        for (const initialItem of initialElements) {
            initialRows.push(initialItem);
        }
        downloadWorkbook(props.columnDefinitions, props.collectionType, initialRows);
    }
}

const name = ref<string>("Sample Sheet for Workflow Input");
if ("name" in props.initialElements) {
    name.value = `${props.initialElements.name} (as sample sheet)` || name.value;
}

initialize();

type ColumnDefinition = components["schemas"]["SampleSheetColumnDefinition"];

function uriFromRow(row: AgRowData): string {
    return row["url"] as string as string;
}

function uri2FromRow(row: AgRowData): string {
    return row["url_1"] as string as string;
}

const elementIdentifiers = computed<string[]>(() => {
    const identifiers: string[] = [];
    for (const row of rowData.value) {
        const elementIdentifier = elementIdentifierFromRow(row);
        if (elementIdentifier) {
            identifiers.push(elementIdentifier);
        }
    }
    return identifiers;
});

function elementIdentifierFromRow(row: AgRowData): string {
    if (mode.value === "model_objects") {
        return (row["__model_object"] as { element_identifier: string }).element_identifier;
    } else {
        return row["list_identifiers"] as string;
    }
}

function attachExtraMetadata(row: AgRowData, urlElement: UrlDataElement, typeIndex: number) {
    // Apply extra metadata from the row to the UrlDataElement

    // typeIndex is 0 for all elements of a simple sample sheet and for the forward element
    // of all paired sample sheets. typeIndex is 1 for the reverse element of paired sample sheets.
    if (extraColumns.value.length > 0) {
        for (const extraColumn of extraColumns.value) {
            const extraValue = row[extraColumn.type] as string | undefined;
            const extraColumnType = extraColumn.type;
            const extraColumnTypeIndex = extraColumn.type_index ?? 0;
            if (extraColumnType == "dbkey") {
                urlElement.dbkey = extraValue || dbKey.value || "?";
            } else if (extraColumnType == "file_type") {
                urlElement.ext = extraValue || extension.value || "auto";
            } else if (extraColumnType == "name" && extraValue) {
                urlElement.name = extraValue;
            } else if (extraColumnType == "tags" && extraValue) {
                urlElement.tags = extraValue.split(",").map((tag) => tag.trim());
            } else if (extraColumnType == "info") {
                urlElement.info = extraValue;
            } else if (extraColumnType == "hash_md5" && typeIndex === extraColumnTypeIndex && extraValue) {
                urlElement.MD5 = extraValue;
            } else if (extraColumnType == "hash_sha1" && typeIndex === extraColumnTypeIndex && extraValue) {
                urlElement["SHA-1"] = extraValue;
            } else if (extraColumnType == "hash_sha256" && typeIndex === extraColumnTypeIndex && extraValue) {
                urlElement["SHA-256"] = extraValue;
            } else if (extraColumnType == "hash_sha512" && typeIndex === extraColumnTypeIndex && extraValue) {
                urlElement["SHA-512"] = extraValue;
            }
        }
    }
}

function urlDataElementWithSelectedMetadata(elementIdentifier: string, uri: string): UrlDataElement {
    const urlElement = urlDataElement(elementIdentifier, uri);
    urlElement.dbkey = dbKey.value || "?";
    urlElement.ext = extension.value || "auto";
    return urlElement;
}

async function attemptCreateViaFetch() {
    const columnDefinitions: ColumnDefinition[] = props.columnDefinitions ?? [];
    const elements: (UrlDataElement | NestedElement)[] = [];
    if (props.collectionType == "sample_sheet") {
        for (const row of rowData.value) {
            const elementIdentifier = elementIdentifierFromRow(row);
            const elementRow = toApiRows(row);
            const uri = uriFromRow(row);
            const element = urlDataElementWithSelectedMetadata(elementIdentifier, uri);
            attachExtraMetadata(row, element, 0);
            element.row = elementRow;
            elements.push(element);
        }
    } else if (
        props.collectionType == "sample_sheet:paired" ||
        props.collectionType == "sample_sheet:paired_or_unpaired"
    ) {
        for (const row of rowData.value) {
            const elementIdentifier = elementIdentifierFromRow(row);
            const elementRow = toApiRows(row);
            const uri = uriFromRow(row);
            const uri2 = uri2FromRow(row);
            let childElements;
            if (uri2) {
                const forwardElement = urlDataElementWithSelectedMetadata("forward", uri);
                attachExtraMetadata(row, forwardElement, 0);
                const reverseElement = urlDataElementWithSelectedMetadata("reverse", uri2);
                attachExtraMetadata(row, reverseElement, 1);
                childElements = [forwardElement, reverseElement];
            } else {
                if (props.collectionType == "sample_sheet:paired") {
                    // Do something better with this exception ideally.
                    throw Error("Unpaired dataset discovered - cannot build collection");
                }
                const unpairedElement = urlDataElementWithSelectedMetadata("unpaired", uri);
                attachExtraMetadata(row, unpairedElement, 0);
                childElements = [unpairedElement];
            }
            const element = nestedElement(elementIdentifier, childElements);
            element.row = elementRow;
            elements.push(element);
        }
    }
    const target: HdcaUploadTarget = {
        destination: { type: "hdca" },
        collection_type: props.collectionType,
        elements: elements,
        column_definitions: columnDefinitions,
        auto_decompress: false, // why is this needed?
        name: name.value,
    };
    emit("on-fetch-target", target);
}

function elementsForCreateApi() {
    const identifiers: CollectionElementIdentifiers = [];
    const collectionType = props.collectionType;
    if (collectionType == "sample_sheet") {
        for (const row of rowData.value) {
            const elementIdentifier = elementIdentifierFromRow(row);
            const element = row["__model_object"] as DCESummary;
            const hda = element.object as HDAObject;
            const identifier = {
                name: elementIdentifier,
                src: "hda" as "hda",
                id: hda.id,
            };
            identifiers.push(identifier);
        }
    } else if (collectionType == "sample_sheet:paired" || collectionType == "sample_sheet:paired_or_unpaired") {
        // TODO:
        for (const row of rowData.value) {
            const elementIdentifier = elementIdentifierFromRow(row);
            const element = row["__model_object"] as DCESummary;
            const childCollection = element.object as DCObject;
            const rowElements = [];
            for (const childElement of childCollection.elements) {
                const childIdentifier = {
                    name: childElement.element_identifier,
                    src: "hda" as "hda",
                    id: childElement.object!.id,
                };
                rowElements.push(childIdentifier);
            }
            const entry = {
                name: elementIdentifier,
                collection_type: childCollection.collection_type,
                src: "new_collection" as "new_collection",
                element_identifiers: rowElements,
            };
            identifiers.push(entry);
        }
    } else {
        console.log("sample_sheet:record not yet implemented, this will fail");
    }
    return identifiers;
}

async function attemptCreateViaExistingObjects() {
    const identifiers: CollectionElementIdentifiers = elementsForCreateApi();
    const collectionType = props.collectionType;
    const hide_source_items = false;
    const payload = createPayload(name.value, collectionType, identifiers, hide_source_items);
    const rows: Record<string, SampleSheetColumnValueT[]> = {};
    for (const row of rowData.value) {
        const elementRow = toApiRows(row);
        rows[elementIdentifierFromRow(row)] = elementRow;
    }
    payload.rows = rows;
    emit("on-collection-create-payload", payload);
}

function toApiRows(row: AgRowData) {
    const elementRow: SampleSheetColumnValueT[] = [];
    (props.columnDefinitions || []).forEach((colDef) => {
        elementRow.push(row[colDef.name] as SampleSheetColumnValueT);
    });
    return elementRow;
}

const { createPayload } = useCollectionCreation();

async function attemptCreate() {
    if (mode.value === "model_objects") {
        attemptCreateViaExistingObjects();
    } else {
        attemptCreateViaFetch();
    }
}

function updateExtension(newExtension: string) {
    extension.value = newExtension;
}

function updateDbKey(newDbKey: string) {
    dbKey.value = newDbKey;
}

defineExpose({ attemptCreate });
</script>

<template>
    <div
        :class="rootClasses"
        @drop.prevent="handleDrop"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false">
        <AgGridVue
            :row-data="rowData"
            :column-defs="columnDefs"
            :default-col-def="defaultColDef"
            :style="style"
            @gridReady="onGridReady" />
        <BRow align-h="center" style="margin-top: 10px">
            <BCol v-if="showExtension" cols="4">
                <span class="upload-footer-title">Type</span>
                <UploadSelectExtension
                    class="upload-footer-extension"
                    :value="extension"
                    :disabled="busy"
                    :list-extensions="listExtensions"
                    @input="updateExtension">
                </UploadSelectExtension>
            </BCol>
            <BCol v-if="showDbKey" cols="4">
                <span class="upload-footer-title">Reference</span>
                <UploadSelect
                    class="upload-footer-genome"
                    :value="dbKey"
                    :disabled="busy"
                    :options="listDbKeys"
                    what="reference"
                    placeholder="Select Reference"
                    @input="updateDbKey" />
            </BCol>
            <BCol cols="4">
                <BInputGroup prepend="Collection Name" class="mb-2" size="sm">
                    <BFormInput
                        v-model="name"
                        :placeholder="localize('Enter a name for your new sample sheet')"
                        size="sm"
                        required />
                </BInputGroup>
            </BCol>
        </BRow>
        <div class="text-center below-grid-link">
            <BLink v-if="!fromWorkbookUpload" @click="downloadSeededWorkbook">
                <FontAwesomeIcon size="xl" :icon="faDownload" />
                Download this as spreadsheet and fill it in outside of Galaxy.
            </BLink>
        </div>
    </div>
</template>

<style scoped>
.below-grid-link {
    padding: 7px;
}
</style>

<style>
// doesn't work with scoped style, newer AG Grid lets specifying style directly
// in ColDef but this deson't seem work with this older AG Grid we're using Vue 2.
.ag-grid-column-has-custom-header-description {
    text-decoration-line: underline;
    text-decoration-style: dashed;
}
</style>
