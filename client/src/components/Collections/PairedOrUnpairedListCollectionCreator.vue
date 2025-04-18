<script setup lang="ts">
import { type ColDef, type GetRowIdParams, type IRowDragItem, type NewValueParams } from "ag-grid-community";
import { BAlert, BCol, BLink, BRow } from "bootstrap-vue";
import { getActivePinia } from "pinia";
import { computed, nextTick, ref } from "vue";

import type { components, CreateNewCollectionPayload, HDASummary, HistoryItemSummary } from "@/api";
import { splitIntoPairedAndUnpaired } from "@/components/Collections/pairing";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import { useAgGrid } from "@/composables/useAgGrid";
import { usePairingDatasetTargetsStore } from "@/stores/collectionBuilderItemsStore";
import localize from "@/utils/localization";

import type { GenericPair } from "../History/adapters/buildCollectionModal";
import { stripExtension, useUpdateIdentifiersForRemoveExtensions } from "./common/stripExtension";
import {
    type SupportedPairedOrPairedBuilderCollectionTypes,
    useCollectionCreator,
} from "./common/useCollectionCreator";
import { usePairingSummary } from "./common/usePairingSummary";
import { type AutoPairingResult, autoPairWithCommonFilters, guessNameForPair } from "./pairing";

import AutoPairing from "./common/AutoPairing.vue";
import PairedOrUnpairedListCreatorHelp from "./PairedOrUnpairedListCreatorHelp.vue";
import CollectionCreator from "@/components/Collections/common/CollectionCreator.vue";

type CollectionElementIdentifier = components["schemas"]["CollectionElementIdentifier"];
type CollectionSourceType = components["schemas"]["ColletionSourceType"];
const NOT_VALID_ELEMENT_MSG: string = localize("is not a valid element for this collection");

const { confirm } = useConfirmDialog();

const pinia = getActivePinia();

const pairingTargetsStore = usePairingDatasetTargetsStore();

interface Props {
    historyId: string;
    initialElements: HistoryItemSummary[];
    defaultHideSourceItems?: boolean;
    suggestedName?: string;
    fromSelection?: boolean;
    extensions?: string[];
    height?: string;
    width?: string;
    forwardFilter?: string;
    reverseFilter?: string;
    collectionType: SupportedPairedOrPairedBuilderCollectionTypes;
    mode: "wizard" | "modal"; // in modal mode we need to show buttons and manage pairing components, wizard takes care these details
}

const props = defineProps<Props>();

const { gridApi, AgGridVue, onGridReady, theme } = useAgGrid(resize);

const { updateIdentifierIfUnchanged } = useUpdateIdentifiersForRemoveExtensions(props);

const showAutoPairing = ref<boolean>(false);

function resize() {
    if (gridApi.value) {
        gridApi.value.sizeColumnsToFit();
    }
}

const emit = defineEmits<{
    (e: "on-create", options: CreateNewCollectionPayload): void;
    (e: "on-cancel"): void;
    (e: "go-to-auto-pairing"): void;
    (e: "name", value: string): void;
    (e: "input-valid", value: boolean): void;
}>();

const currentForwardFilter = ref(props.forwardFilter);
const currentReverseFilter = ref(props.reverseFilter);
const activeElements = ref(props.initialElements);
const { currentSummary, summaryText, autoPair } = usePairingSummary<HistoryItemSummary>(props);

const {
    removeExtensions,
    hideSourceItems,
    isElementInvalid,
    onUpdateHideSourceItems,
    collectionName,
    onUpdateCollectionName,
    onCollectionCreate,
    showButtonsForModal,
    showHid,
    showElementExtension,
} = useCollectionCreator(props, emit);

pairingTargetsStore.setShowElementExtension(showElementExtension);

const style = computed(() => {
    return { width: props.width || "100%", height: props.height || "500px" };
});

const flatLists = computed(() => props.collectionType.indexOf("paired") == -1);

const isNestedList = computed(() => {
    return props.collectionType.startsWith("list:list");
});

const collectionTypeForAutoPairing = computed<"list:paired" | "list:paired_or_unpaired">(() => {
    return props.collectionType == "list:paired_or_unpaired" ? "list:paired_or_unpaired" : "list:paired";
});

// Default Column Properties
const defaultColDef = ref<ColDef>({
    editable: false,
    sortable: false,
    filter: false,
    resizable: true,
});

type StatusType = "ok" | "duplicate" | "requires_pairing";

type UnpairedDataset = { unpaired: HistoryItemSummary };

interface RowT {
    id: string;
    datasets: GenericPair<HistoryItemSummary> | UnpairedDataset;
    identifier: string;
    outerIdentifier?: string;
    status: StatusType;
}

const rowData = ref<RowT[]>([]);

const columnDefs = computed(() => {
    let datasets: ColDef;
    if (!flatLists.value) {
        datasets = {
            headerName: "Dataset(s)",
            field: "datasets",
            editable: false,
            cellRenderer: "PairedDatasetCellComponent",
            rowDrag: true,
        };
    } else {
        datasets = {
            headerName: "Dataset",
            field: "datasets",
            editable: false,
            rowDrag: true,
            valueFormatter: (p) => {
                if (showHid) {
                    return `${p.value.unpaired.hid}: ${p.value.unpaired.name}`;
                } else {
                    return p.value.unpaired.name;
                }
            },
        };
    }
    const identifierColumns: ColDef[] = [];
    if (!isNestedList.value) {
        identifierColumns.push({
            headerName: "List Identifier",
            field: "identifier",
            editable: true,
            onCellValueChanged: onIdentifierChange,
        });
    } else {
        identifierColumns.push({
            headerName: "Outer List Identifier",
            field: "outerIdentifier",
            editable: true,
            onCellValueChanged: onIdentifierChange,
        });
        identifierColumns.push({
            headerName: "Inner List Identifier",
            field: "identifier",
            editable: true,
            onCellValueChanged: onIdentifierChange,
        });
    }
    const discard: ColDef = {
        headerName: "Discard",
        field: "discard",
        editable: false,
        cellRenderer: "CellDiscardComponent",
        width: 65,
    };
    const status: ColDef = {
        headerName: "Status",
        field: "status",
        editable: false,
        cellRenderer: "CellStatusComponent",
        width: 65,
    };
    return [datasets, ...identifierColumns, discard, status];
});

function onIdentifierChange(e: NewValueParams) {
    nextTick(() => {
        checkForDuplicates(true);
    });
}

function checkForDuplicates(refresh: boolean) {
    const isNested = isNestedList.value;

    function identifierKey(item: RowT): string {
        // duplicate checking for nested collections is trickier - need to check combination
        // of keys is unique instead.
        if (isNested) {
            return `${item.outerIdentifier ?? ""}:${item.identifier}`;
        } else {
            return item.identifier;
        }
    }

    const isDuplicate: Record<string, boolean> = {};
    let anyDuplicated = false;
    for (const item of rowData.value) {
        const identifier = identifierKey(item);
        if (identifier in isDuplicate) {
            isDuplicate[identifier] = true;
            anyDuplicated = true;
        } else {
            isDuplicate[identifier] = false;
        }
    }
    for (const item of rowData.value) {
        const identifier = identifierKey(item);
        if (item.status == "ok" || item.status == "duplicate") {
            item.status = isDuplicate[identifier] ? "duplicate" : "ok";
        }
    }
    if (refresh) {
        _refresh();
        gridApi.value?.redrawRows();
    }
    return anyDuplicated;
}

function unpairedRow(item: HistoryItemSummary): RowT {
    let name = item.name || "";
    if (removeExtensions.value) {
        name = stripExtension(name);
    }
    let status: StatusType = "ok";
    if (props.collectionType.endsWith(":paired")) {
        status = "requires_pairing";
    }
    return { identifier: name || "", datasets: { unpaired: item }, id: item.id, status: status };
}

function pairedRow(item: GenericPair<HistoryItemSummary>): RowT {
    return { identifier: item.name, datasets: item, id: item.forward.id, status: "ok" };
}

function syncPairingToRowData(summary: AutoPairingResult<HistoryItemSummary>, rowDataValue: RowT[]) {
    if (!flatLists.value) {
        if (summary) {
            for (const pair of summary.pairs) {
                rowDataValue.push(pairedRow(pair));
            }
            for (const unpaired of summary.unpaired) {
                rowDataValue.push(unpairedRow(unpaired));
            }
        } else {
            for (const unpaired of activeElements.value) {
                rowDataValue.push(unpairedRow(unpaired));
            }
        }
    } else {
        for (const unpaired of activeElements.value) {
            rowDataValue.push(unpairedRow(unpaired));
        }
    }
}

function syncRowDataToRowPairing() {
    rowData.value.splice(0);
    const summary = currentSummary.value;
    if (summary) {
        syncPairingToRowData(summary, rowData.value);
    }
}

function initialize() {
    if (currentForwardFilter.value === undefined) {
        const summary = autoPairWithCommonFilters(activeElements.value, true);
        const { forwardFilter, reverseFilter } = summary;
        if (forwardFilter !== undefined && reverseFilter !== undefined) {
            currentSummary.value = summary;
            currentForwardFilter.value = forwardFilter;
            currentReverseFilter.value = reverseFilter;
        } else {
            autoPair(activeElements.value, "", "", removeExtensions.value);
        }
    } else {
        autoPair(
            activeElements.value,
            currentForwardFilter.value,
            currentReverseFilter.value || "",
            removeExtensions.value
        );
    }
    syncRowDataToRowPairing();
    checkForDuplicates(false);
}

initialize();

function getRowId(params: GetRowIdParams) {
    return String(params.data.id);
}

function addUploadedFiles(files: HDASummary[]) {
    // Any uploaded files are added to workingElements in _elementsSetUp
    // The user will have to manually select the files to add them to the pair

    // Check for validity of uploads
    const addedFiles = [];
    files.forEach((file) => {
        const problem = isElementInvalid(file);
        if (problem) {
            const invalidMsg = `${file.hid}: ${file.name} ${problem} and ${NOT_VALID_ELEMENT_MSG}`;
            Toast.error(invalidMsg, localize("Uploaded item invalid for pair"));
        } else {
            activeElements.value.push(file);
            addedFiles.push(file);
        }
    });
    if (currentForwardFilter.value === undefined) {
        // Auto-pairing hasn't paired anything yet - just take all the files and try them...
        initialize();
    } else {
        const summary = splitIntoPairedAndUnpaired(
            files,
            currentForwardFilter.value || "",
            currentReverseFilter.value || "",
            removeExtensions.value
        );
        syncPairingToRowData(summary, rowData.value);
    }
    _refresh();
}

function updatePairNames() {
    return (rowData.value || []).map((v) => {
        if ("forward" in v.datasets) {
            const previousRemoveExtensions = !removeExtensions.value;
            const previousUnchangedIdentifier = guessNameForPair(
                v.datasets.forward,
                v.datasets.reverse,
                currentForwardFilter.value || "",
                currentReverseFilter.value || "",
                previousRemoveExtensions
            );
            if (v.identifier == previousUnchangedIdentifier) {
                v.identifier = guessNameForPair(
                    v.datasets.forward,
                    v.datasets.reverse,
                    currentForwardFilter.value || "",
                    currentReverseFilter.value || "",
                    removeExtensions.value
                );
            }
        } else {
            updateIdentifierIfUnchanged(v, removeExtensions.value);
        }
    });
}

function removeExtensionsToggle() {
    removeExtensions.value = !removeExtensions.value;
    updatePairNames();
    _refresh();
    gridApi.value?.redrawRows();
}

function flatListIdentifiers(): CollectionElementIdentifier[] {
    const outerIdentifiers: Record<string, RowT[]> = {};
    for (const row of rowData.value) {
        const outerIdentifier = row.outerIdentifier || "";
        if (!(outerIdentifier in outerIdentifiers)) {
            outerIdentifiers[outerIdentifier] = [];
        }
        outerIdentifiers[outerIdentifier]?.push(row);
    }
    const listIdentifiers: CollectionElementIdentifier[] = [];
    for (const outerIdentifier of Object.keys(outerIdentifiers)) {
        const outerIdentifierElements = [];
        for (const innerRowData of outerIdentifiers[outerIdentifier] ?? []) {
            const unpaired = unpairedDataset(innerRowData);
            const innerElement = {
                name: innerRowData.identifier,
                id: unpaired.id as string,
                src: ("src" in unpaired ? unpaired.src : "hda") as CollectionSourceType,
            };
            outerIdentifierElements.push(innerElement);
        }

        listIdentifiers.push({
            collection_type: "list",
            src: "new_collection" as CollectionSourceType,
            name: outerIdentifier,
            element_identifiers: outerIdentifierElements,
        });
    }

    return listIdentifiers;
}

function pairedListIdentifiers(): CollectionElementIdentifier[] {
    let rows = rowData.value || [];
    const strictPairs = props.collectionType.endsWith(":paired");
    if (strictPairs) {
        rows = rows.filter((value) => !("unpaired" in value.datasets));
    }
    return rows.map((v) => {
        const isPaired = "forward" in v.datasets;
        function toElementIdentifierObject(
            collectionType: "paired" | "paired_or_unpaired",
            identifiers: CollectionElementIdentifier[]
        ) {
            return {
                collection_type: collectionType,
                src: "new_collection" as CollectionSourceType,
                name: v.identifier as string,
                element_identifiers: identifiers,
            };
        }
        if (isPaired) {
            const pair = v.datasets as GenericPair<HistoryItemSummary>;
            const identifiers: CollectionElementIdentifier[] = [
                {
                    name: "forward",
                    id: pair.forward.id as string,
                    src: ("src" in pair.forward ? pair.forward.src : "hda") as CollectionSourceType,
                },
                {
                    name: "reverse",
                    id: pair.reverse.id as string,
                    src: ("src" in pair.reverse ? pair.reverse.src : "hda") as CollectionSourceType,
                },
            ];
            return toElementIdentifierObject(
                props.collectionType == "list:paired" ? "paired" : "paired_or_unpaired",
                identifiers
            );
        } else {
            const unpaired = unpairedDataset(v);
            const identifiers = [
                {
                    name: "unpaired",
                    id: unpaired.id as string,
                    src: ("src" in unpaired ? unpaired.src : "hda") as CollectionSourceType,
                },
            ];
            return toElementIdentifierObject(strictPairs ? "paired" : "paired_or_unpaired", identifiers);
        }
    });
}

function unpairedDataset(row: RowT): HistoryItemSummary {
    if ("unpaired" in row.datasets) {
        return row.datasets.unpaired;
    } else {
        throw Error("Unknown data encountered, logic bug in Galaxy's client.");
    }
}

async function attemptCreate() {
    if (checkForDuplicates(true)) {
        return;
    }

    let listIdentifiers: CollectionElementIdentifier[];
    if (props.collectionType == "list:list") {
        listIdentifiers = flatListIdentifiers();
    } else {
        listIdentifiers = pairedListIdentifiers();
    }
    let confirmed = false;
    if (listIdentifiers.length == 0) {
        confirmed = await confirm("Are you sure you want to create a list with no entries?", {
            title: "Create an empty list",
            okTitle: "Create",
            okVariant: "primary",
        });
        if (!confirmed) {
            return;
        }
    }

    onCollectionCreate(props.collectionType, listIdentifiers);
}

defineExpose({ attemptCreate, redraw: resize });

function applyFilters(forwardFilter: string, reverseFilter: string) {
    currentForwardFilter.value = forwardFilter;
    currentReverseFilter.value = reverseFilter;
    showAutoPairing.value = false;
    initialize();
}

// two ways to pair, can drag and drop rows or more accessible can just click links in
// pairs. This type is used to indicate what type of pairing is occurring.
type PairBy = "click" | "drag_and_drop";
// do you drag forward to reverse or drag reverse to forward, I'm not sure what is more intuitive
// so leaving this configurable for now - not by the user but in the code. Same with clicking,
// do you click first than second or second than first. Here I think it makes a bit more sense
// to click forward to reverse.
type PairDirection = "from_1_to_2" | "from_2_to_1";
const pairDirections: Record<PairBy, PairDirection> = {
    click: "from_1_to_2",
    drag_and_drop: "from_1_to_2",
};
// when dragging - do you insert the pair at the drop target ("2") or at where the dragging
// starting from ("1") - this is independent of what is forward or reverse. Likewise if pairing
// by clicking, do you do that from the first click ("1") or the second click ("2")
const insertPairAtIndexType: Record<PairBy, "1" | "2"> = {
    click: "2",
    drag_and_drop: "2",
};

function onPair(firstId: string, secondId: string, pairBy: PairBy) {
    // if pairBy is click -> firstId is the first thing clicked, secondId is the second
    // if pairBy is drag_and_drop -> firstId is what is being dragged, secondId is what it is dragged to
    let firstIndex = -1;
    let secondIndex = -1;
    let forward: HistoryItemSummary | null = null;
    let reverse: HistoryItemSummary | null = null;

    const pairDirection = pairDirections[pairBy];
    rowData.value.forEach((row, index) => {
        if (row.id == firstId && "unpaired" in row.datasets) {
            firstIndex = index;
            if (pairDirection == "from_1_to_2") {
                forward = row.datasets.unpaired as HistoryItemSummary;
            } else {
                reverse = row.datasets.unpaired as HistoryItemSummary;
            }
        }
        if (row.id == secondId && "unpaired" in row.datasets) {
            secondIndex = index;
            if (pairDirection == "from_1_to_2") {
                reverse = row.datasets.unpaired as HistoryItemSummary;
            } else {
                forward = row.datasets.unpaired as HistoryItemSummary;
            }
        }
    });

    if (firstIndex !== -1 && secondIndex !== -1 && forward && reverse) {
        const nameForPair = guessNameForPair(
            forward,
            reverse,
            currentForwardFilter.value || "",
            currentReverseFilter.value || "",
            removeExtensions.value
        );
        const pair = { forward, reverse, name: nameForPair };
        const insertPairAt = insertPairAtIndexType[pairBy];
        let targetIndex;
        // try to splice the targets so the pair ends up at the correct spot
        // based on insertPairAtIndexType (does it replace the first element
        // or the second element).
        if (insertPairAt == "1") {
            if (firstIndex < secondIndex) {
                targetIndex = firstIndex;
            } else {
                targetIndex = firstIndex - 1;
            }
        } else {
            if (secondIndex < firstIndex) {
                targetIndex = secondIndex;
            } else {
                targetIndex = secondIndex - 1;
            }
        }
        // need to remove the latter item first to preserve indices
        if (firstIndex < secondIndex) {
            rowData.value.splice(secondIndex, 1);
            rowData.value.splice(firstIndex, 1);
        } else {
            rowData.value.splice(firstIndex, 1);
            rowData.value.splice(secondIndex, 1);
        }
        rowData.value.splice(targetIndex, 0, pairedRow(pair));
        _refresh();

        // reset pairing targets and such... even if coming from drag_and_drop reset this
        // because we might have paired the current target with a drag and drop.
        activeUnpairedTarget.value = null;
        pairingTargetsStore.resetUnpairedTarget();
    }
}

function _refresh() {
    gridApi.value!.setRowData(rowData.value);
}

function onUnpair(pair: GenericPair<HistoryItemSummary>) {
    const targetIndex = onRemove(pair, false) || 0;
    rowData.value.splice(targetIndex, 0, unpairedRow(pair.forward), unpairedRow(pair.reverse));
    _refresh();
}

type UnpairedValue = { unpaired: HistoryItemSummary };

const activeUnpairedTarget = ref<UnpairedValue | null>(null);

function onUnpairedClick(value: UnpairedValue) {
    if (activeUnpairedTarget.value == null) {
        activeUnpairedTarget.value = value;
        pairingTargetsStore.setUnpairedTarget(value.unpaired.id);
    } else {
        const forwardId = activeUnpairedTarget.value.unpaired.id;
        const reverseId = value.unpaired.id;
        if (forwardId == reverseId) {
            // cannot pair an element with itself, assuming user wants to make this no longer
            // the active target
            activeUnpairedTarget.value = null;
            pairingTargetsStore.resetUnpairedTarget();
            return;
        } else {
            onPair(forwardId, reverseId, "click");
        }
    }
}

function onRemove(item: GenericPair<HistoryItemSummary> | UnpairedValue, refresh = true) {
    let rowId = null as string | null;
    if ("forward" in item) {
        rowId = item.forward.id;
    } else {
        rowId = item.unpaired.id;
    }
    let targetIndex = null;
    rowData.value.forEach((row, index) => {
        if (row.id == rowId) {
            targetIndex = index;
        }
    });
    if (targetIndex !== null) {
        rowData.value.splice(targetIndex, 1);
    }
    if (refresh) {
        _refresh();
    }
    return targetIndex;
}

const unpairedProblemDatasetCount = computed(() => {
    if (!props.collectionType.endsWith(":paired")) {
        return 0;
    }
    let count = 0;
    rowData.value.forEach((v) => {
        if ("unpaired" in v.datasets) {
            count += 1;
        }
    });
    return count;
});

function dismissUnmatchedDatasets() {
    const toRemove: UnpairedDataset[] = [];
    rowData.value.forEach((v) => {
        if ("unpaired" in v.datasets) {
            toRemove.push(v.datasets);
        }
    });
    toRemove.forEach((v) => {
        onRemove(v, false);
    });
    _refresh();
}

function onSwap(pair: GenericPair<HistoryItemSummary>) {
    const newForward = pair.reverse;
    pair.reverse = pair.forward;
    pair.forward = newForward;
}

function goToAutoPairing() {
    if (props.mode === "wizard") {
        emit("go-to-auto-pairing");
    } else {
        showAutoPairing.value = true;
    }
}

function rowDragText(params: IRowDragItem) {
    return params.rowNode?.data.identifier;
}

const context = {
    pinia,
    onPair,
    onUnpair,
    onUnpairedClick,
    onRemove,
    onSwap,
};
</script>

<script lang="ts">
// eslint-disable-next-line import/first
import { components as VueComponents } from "./PairedOrUnpairedComponents";

// defineExpose should work for exposing PairedDatasetCellComponent to AG Grid
// but doesn't seem to and it has been reported as an issue with Vue 2.7.
export default {
    components: VueComponents,
};
</script>

<template>
    <div>
        <div v-if="showAutoPairing">
            <AutoPairing
                :elements="initialElements"
                :collection-type="collectionTypeForAutoPairing"
                :remove-extensions="removeExtensions"
                :forward-filter="currentForwardFilter"
                :reverse-filter="currentReverseFilter"
                :mode="mode"
                :show-hid="showHid"
                :extensions="extensions"
                @on-apply="applyFilters"
                @on-cancel="showAutoPairing = false" />
        </div>
        <CollectionCreator
            v-else
            :oncancel="() => emit('on-cancel')"
            :history-id="props.historyId"
            :hide-source-items="hideSourceItems"
            render-extensions-toggle
            :extensions-toggle="removeExtensions"
            :extensions="extensions"
            collection-type="collectionType"
            :no-items="props.initialElements.length == 0 && !props.fromSelection"
            :show-upload="!fromSelection"
            :show-buttons="showButtonsForModal"
            :collection-name="collectionName"
            :mode="mode"
            @on-update-collection-name="onUpdateCollectionName"
            @add-uploaded-files="addUploadedFiles"
            @onUpdateHideSourceItems="onUpdateHideSourceItems"
            @clicked-create="attemptCreate"
            @remove-extensions-toggle="removeExtensionsToggle">
            <template v-slot:help-content>
                <PairedOrUnpairedListCreatorHelp
                    :from-selection="props.fromSelection"
                    :collection-type="props.collectionType"
                    :mode="mode" />
            </template>
            <template v-slot:middle-content>
                <div>
                    <BRow v-if="!flatLists">
                        <BCol>
                            <BAlert show variant="info" dismissible>
                                {{ summaryText }}
                                If this isn't correct,
                                <BLink style="font-weight: bold" @click="goToAutoPairing">configure auto-pairing</BLink
                                >.
                            </BAlert>
                        </BCol>
                    </BRow>
                    <BRow v-if="unpairedProblemDatasetCount > 0">
                        <BCol>
                            <BAlert show variant="warning" dismissible>
                                {{ unpairedProblemDatasetCount }} unmatched datasets, these should be either dismissed
                                or paired off.
                                <BLink
                                    style="font-weight: bold"
                                    data-description="dismiss unmatched datasets"
                                    @click="dismissUnmatchedDatasets"
                                    >Click here to discard all remaining unpaired datasets.</BLink
                                >
                            </BAlert>
                        </BCol>
                    </BRow>
                    <div :style="style" :class="theme">
                        <AgGridVue
                            :row-drag-managed="true"
                            :row-drag-text="rowDragText"
                            :get-row-id="getRowId"
                            :default-col-def="defaultColDef"
                            :column-defs="columnDefs"
                            :style="style"
                            :row-data="rowData"
                            :context="context"
                            @gridReady="onGridReady" />
                    </div>
                </div>
            </template>
        </CollectionCreator>
    </div>
</template>
