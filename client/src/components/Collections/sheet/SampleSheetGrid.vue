<script lang="ts" setup>
import { faDownload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import type { ColDef, ValueSetterParams } from "ag-grid-community";
import { BCol, BFormInput, BInputGroup, BLink, BRow } from "bootstrap-vue";
import { computed, ref } from "vue";

import type {
    CollectionElementIdentifiers,
    CreateNewCollectionPayload,
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
import { enforceColumnUniqueness, useGridHelpers } from "@/components/Landing/gridHelpers";
import { Toast } from "@/composables/toast";
import { useUploadConfigurations } from "@/composables/uploadConfigurations";
import { useAgGrid } from "@/composables/useAgGrid";
import localize from "@/utils/localization";

import {
    type AgRowData,
    modelObjectIdentifierColumn,
    parseSampleSheetValue,
    SAMPLE_SHEET_GRID_STYLE,
    toAgGridColumnDefinition,
    type UriRow,
    useSampleSheetGrid,
} from "./useSampleSheetGrid";

import UploadSelect from "@/components/Upload/UploadSelect.vue";
import UploadSelectExtension from "@/components/Upload/UploadSelectExtension.vue";

interface Props {
    currentHistoryId: string;
    collectionType: SampleSheetCollectionType;
    columnDefinitions: SampleSheetColumnDefinitions;
    initialElements: InitialElements;
    busy: boolean;
    extensions?: string[] | undefined;
}

const props = withDefaults(defineProps<Props>(), {
    extensions: undefined,
});

const emit = defineEmits<{
    (e: "workbook-contents", base64Content: string): void;
    (e: "on-fetch-target", target: HdcaUploadTarget): void;
    (e: "on-collection-create-payload", payload: CreateNewCollectionPayload): void;
}>();

// Upload properties
const uploadConfigurations = useUploadConfigurations(props.extensions);
const { effectiveExtensions, listDbKeys } = uploadConfigurations;
const { makeExtensionColumn, makeDbkeyColumn } = useGridHelpers(uploadConfigurations);
const extension = ref("auto");
const dbKey = ref("?");
const listExtensions = computed(() => effectiveExtensions.value.filter((ext) => !ext.composite_files));

const mode = computed<"uris" | "model_objects">(() => ("elements" in props.initialElements ? "model_objects" : "uris"));

const isPaired = computed(
    () => props.collectionType === "sample_sheet:paired" || props.collectionType === "sample_sheet:paired_or_unpaired",
);

const fromWorkbookUpload = computed(() => "rows" in props.initialElements);

const extraColumns = computed<ParsedFetchWorkbookColumn[]>(() =>
    "rows" in props.initialElements ? props.initialElements.extra_columns || [] : [],
);

const columnDefinitionList = computed<SampleSheetColumnDefinition[]>(() => props.columnDefinitions ?? []);

function initialColumnValues(): Record<string, SampleSheetColumnValueT | null> {
    return Object.fromEntries(columnDefinitionList.value.map((colDef) => [colDef.name, initialValue(colDef)]));
}

function uriRow(initialElement: string[]): UriRow {
    const row: UriRow = { url: initialElement[0]!, list_identifiers: "" };
    if (isPaired.value) {
        row["url_1"] = initialElement[1];
        row["list_identifiers"] = initialElement[2] || "";
    } else if (props.collectionType === "sample_sheet") {
        row["list_identifiers"] = initialElement[1] || "";
    } else {
        throw new Error("Collection type not implemented yet");
    }
    return { ...row, ...initialColumnValues() };
}

const { rowData } = useSampleSheetGrid(() => {
    const initialElements = props.initialElements;
    if ("rows" in initialElements) {
        // The workbook parser supplies URI and identifier fields in its open-ended row schema.
        return initialElements.rows.map((parsedRow) => ({ ...parsedRow }) as UriRow);
    } else if ("elements" in initialElements) {
        return initialElements.elements.map((element) => ({ __model_object: element, ...initialColumnValues() }));
    } else {
        return initialElements.map(uriRow);
    }
});

function elementIdentifierFromRow(row: AgRowData): string {
    return row.__model_object ? row.__model_object.element_identifier : row.list_identifiers;
}

const elementIdentifiers = computed<string[]>(() => rowData.value.map(elementIdentifierFromRow).filter(Boolean));

const URI_COLUMN_HEADERS: Partial<Record<SampleSheetCollectionType, string[]>> = {
    sample_sheet: ["URI"],
    "sample_sheet:paired": ["URI 1 (Forward)", "URI 2 (Reverse)"],
    "sample_sheet:paired_or_unpaired": ["URI 1 (Forward)", "URI 2 (Optional/Reverse)"],
};
const URI_FIELDS = ["url", "url_1"];

function leadingColumns(): ColDef[] {
    if (mode.value === "model_objects") {
        return [modelObjectIdentifierColumn("Identifier (Unique Name)")];
    }
    const headers = URI_COLUMN_HEADERS[props.collectionType];
    if (!headers) {
        throw new Error("Mode not implemented yet");
    }
    const uriColumns: ColDef[] = headers.map((headerName, index) => ({
        headerName,
        field: URI_FIELDS[index],
        editable: false,
    }));
    const identifierColumn: ColDef = { headerName: "Element identifier", field: "list_identifiers", editable: true };
    enforceColumnUniqueness(identifierColumn);
    return [...uriColumns, identifierColumn];
}

function setCellValue(params: ValueSetterParams, columnDefinition: SampleSheetColumnDefinition): boolean {
    const parsed = parseSampleSheetValue(params.newValue, columnDefinition);
    if (parsed.valid) {
        params.data[params.colDef.field!] = parsed.value;
    } else {
        Toast.error(`Invalid value for column "${columnDefinition.name}".`);
    }
    return parsed.valid;
}

function metadataColumn(colDef: SampleSheetColumnDefinition): ColDef {
    const column: ColDef = {
        ...toAgGridColumnDefinition(colDef),
        editable: true,
        valueSetter: (params) => setCellValue(params, colDef),
    };
    if (colDef.type === "element_identifier") {
        column.cellEditor = "agSelectCellEditor";
        column.cellEditorParams = () => ({
            values: colDef.optional ? ["", ...elementIdentifiers.value] : elementIdentifiers.value,
        });
    } else if (colDef.restrictions && colDef.type === "string") {
        column.cellEditor = "agSelectCellEditor";
        column.cellEditorParams = { values: colDef.restrictions };
    }
    return column;
}

function extraColumn(column: ParsedFetchWorkbookColumn): ColDef {
    const colDef: ColDef = { headerName: column.title, field: column.type, editable: true };
    if (column.type === "file_type") {
        makeExtensionColumn(colDef);
    } else if (column.type === "dbkey") {
        makeDbkeyColumn(colDef);
    }
    if (typeof colDef.valueSetter === "function") {
        const validate = colDef.valueSetter;
        colDef.valueSetter = (params) => {
            // Blank workbook cells use the sheet's upload defaults.
            if (params.newValue === "" || params.newValue == null) {
                params.data[params.colDef.field!] = "";
                return true;
            }
            return validate(params);
        };
    }
    return colDef;
}

const columnDefs = computed<ColDef[]>(() => [
    ...leadingColumns(),
    ...columnDefinitionList.value.map(metadataColumn),
    ...extraColumns.value.map(extraColumn),
]);

const defaultColDef: ColDef = {
    editable: true,
    sortable: true,
    filter: true,
    resizable: true,
};

const { AgGridVue, onGridReady, theme } = useAgGrid();

const { handleDrop, isDragging } = useWorkbookDropHandling(async (base64Content: string) => {
    emit("workbook-contents", base64Content);
});

function downloadSeededWorkbook() {
    const initialElements = props.initialElements;
    if ("rows" in initialElements) {
        // the download link isn't shown for uploaded workbooks
    } else if ("elements" in initialElements) {
        downloadWorkbookForCollection(props.columnDefinitions, initialElements.id);
    } else {
        downloadWorkbook(props.columnDefinitions, props.collectionType, [...initialElements]);
    }
}

const name = ref<string>(
    "name" in props.initialElements && props.initialElements.name
        ? `${props.initialElements.name} (as sample sheet)`
        : "Sample Sheet for Workflow Input",
);

function toApiRow(row: AgRowData): SampleSheetColumnValueT[] {
    return columnDefinitionList.value.map((colDef) => row[colDef.name] as SampleSheetColumnValueT);
}

function attachExtraMetadata(row: AgRowData, urlElement: UrlDataElement, typeIndex: number) {
    // Apply extra metadata from the row to the UrlDataElement

    // typeIndex is 0 for all elements of a simple sample sheet and for the forward element
    // of all paired sample sheets. typeIndex is 1 for the reverse element of paired sample sheets.
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

function urlElementForRow(row: AgRowData, elementIdentifier: string, uri: string, typeIndex: number): UrlDataElement {
    const urlElement = urlDataElement(elementIdentifier, uri);
    urlElement.dbkey = dbKey.value || "?";
    urlElement.ext = extension.value || "auto";
    attachExtraMetadata(row, urlElement, typeIndex);
    return urlElement;
}

function fetchElementForRow(row: AgRowData): UrlDataElement | NestedElement {
    if (row.__model_object) {
        throw new Error("Cannot fetch a model object row");
    }
    const elementIdentifier = elementIdentifierFromRow(row);
    const uri = row.url;
    let element: UrlDataElement | NestedElement;
    if (!isPaired.value) {
        element = urlElementForRow(row, elementIdentifier, uri, 0);
    } else {
        const uri2 = row.url_1;
        let childElements;
        if (uri2) {
            childElements = [urlElementForRow(row, "forward", uri, 0), urlElementForRow(row, "reverse", uri2, 1)];
        } else {
            if (props.collectionType == "sample_sheet:paired") {
                // Do something better with this exception ideally.
                throw Error("Unpaired dataset discovered - cannot build collection");
            }
            childElements = [urlElementForRow(row, "unpaired", uri, 0)];
        }
        element = nestedElement(elementIdentifier, childElements);
    }
    element.row = toApiRow(row);
    return element;
}

function attemptCreateViaFetch() {
    const target: HdcaUploadTarget = {
        destination: { type: "hdca" },
        collection_type: props.collectionType,
        elements: rowData.value.map(fetchElementForRow),
        column_definitions: columnDefinitionList.value,
        auto_decompress: false, // why is this needed?
        name: name.value,
    };
    emit("on-fetch-target", target);
}

function elementsForCreateApi(): CollectionElementIdentifiers {
    if (props.collectionType == "sample_sheet") {
        return rowData.value.map((row) => {
            const hda = row.__model_object?.object;
            if (!hda || hda.model_class === "DatasetCollection") {
                throw new Error("Expected a dataset row");
            }
            return { name: elementIdentifierFromRow(row), src: "hda" as const, id: hda.id };
        });
    } else if (isPaired.value) {
        return rowData.value.map((row) => {
            const childCollection = row.__model_object?.object;
            if (!childCollection || childCollection.model_class !== "DatasetCollection") {
                throw new Error("Expected a collection row");
            }
            return {
                name: elementIdentifierFromRow(row),
                collection_type: childCollection.collection_type,
                src: "new_collection" as const,
                element_identifiers: childCollection.elements.map((childElement) => ({
                    name: childElement.element_identifier,
                    src: "hda" as const,
                    id: childElement.object!.id,
                })),
            };
        });
    } else {
        console.log("sample_sheet:record not yet implemented, this will fail");
        return [];
    }
}

const { createPayload } = useCollectionCreation();

function attemptCreateViaExistingObjects() {
    const payload = createPayload(name.value, props.collectionType, elementsForCreateApi(), false);
    payload.rows = Object.fromEntries(rowData.value.map((row) => [elementIdentifierFromRow(row), toApiRow(row)]));
    payload.column_definitions = props.columnDefinitions;
    emit("on-collection-create-payload", payload);
}

function attemptCreate() {
    if (mode.value === "model_objects") {
        attemptCreateViaExistingObjects();
    } else {
        attemptCreateViaFetch();
    }
}

defineExpose({ attemptCreate });
</script>

<template>
    <div
        :class="[theme, 'dropzone', { highlight: isDragging }]"
        @drop.prevent="handleDrop"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false">
        <AgGridVue
            v-model="rowData"
            :column-defs="columnDefs"
            :default-col-def="defaultColDef"
            :style="SAMPLE_SHEET_GRID_STYLE"
            @gridReady="onGridReady" />
        <BRow align-h="center" style="margin-top: 10px">
            <BCol v-if="mode === 'uris'" cols="4">
                <span class="upload-footer-title">Type</span>
                <UploadSelectExtension
                    class="upload-footer-extension"
                    :value="extension"
                    :disabled="busy"
                    :list-extensions="listExtensions"
                    @input="extension = $event">
                </UploadSelectExtension>
            </BCol>
            <BCol v-if="mode === 'uris'" cols="4">
                <span class="upload-footer-title">Reference</span>
                <UploadSelect
                    class="upload-footer-genome"
                    :value="dbKey"
                    :disabled="busy"
                    :options="listDbKeys"
                    what="reference"
                    placeholder="Select Reference"
                    @input="dbKey = $event" />
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

:deep(.ag-grid-column-has-custom-header-description) {
    text-decoration-line: underline;
    text-decoration-style: dashed;
}
</style>
