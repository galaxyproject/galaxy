<script setup lang="ts">
import { BAlert, BCardGroup, BLink } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, nextTick, ref, watch } from "vue";

import type { CreateNewCollectionPayload, HDCADetailed } from "@/api";
import {
    createHistoryDatasetCollectionInstanceFull,
    fetchCollectionDetails,
    type SampleSheetCollectionType,
} from "@/api/datasetCollections";
import type { FetchDataPayload, HdcaUploadTarget } from "@/api/tools";
import { stripExtension } from "@/components/Collections/common/stripExtension";
import { useWorkbookDropHandling } from "@/components/Collections/common/useWorkbooks";
import { downloadWorkbook, parseWorkbook, withAutoListIdentifiers } from "@/components/Collections/sheet/workbooks";
import type {
    AnyParsedSampleSheetWorkbook,
    InitialElements,
    PrefixColumnsType,
} from "@/components/Collections/wizard/types";
import { useWizard } from "@/components/Common/Wizard/useWizard";
import type { ExtendedCollectionType } from "@/components/Form/Elements/FormData/types";
import { useFetchJobMonitor } from "@/composables/fetch";
import { useHistoryStore } from "@/stores/historyStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { attemptCreate, type CollectionCreatorComponent } from "./common/useCollectionCreator";
import { useAutoPairing } from "./usePairing";
import type { RulesSourceFrom } from "./wizard/types";
import { useFileSetSources } from "./wizard/useFileSetSources";

import SampleSheetGrid from "./sheet/SampleSheetGrid.vue";
import PasteData from "./wizard/PasteData.vue";
import SelectCollection from "./wizard/SelectCollection.vue";
import SelectDataset from "./wizard/SelectDataset.vue";
import SelectFolder from "./wizard/SelectFolder.vue";
import SourceFromCollection from "./wizard/SourceFromCollection.vue";
import SourceFromDatasetAsTable from "./wizard/SourceFromDatasetAsTable.vue";
import SourceFromPastedData from "./wizard/SourceFromPastedData.vue";
import SourceFromRemoteFiles from "./wizard/SourceFromRemoteFiles.vue";
import SourceFromWorkbook from "./wizard/SourceFromWorkbook.vue";
import UploadSampleSheet from "./wizard/UploadSampleSheet.vue";
import GenericWizard from "@/components/Common/Wizard/GenericWizard.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const historyStore = useHistoryStore();
const { currentHistoryId } = storeToRefs(historyStore);

const sourceIsBusy = ref<boolean>(false);
const workbookCompleted = ref<boolean>(false);
const { pasteData, tabularDatasetContents, uris, setRemoteFilesFolder, onFtp, setDatasetContents, setPasteTable } =
    useFileSetSources(sourceIsBusy);

interface Props {
    collectionType: SampleSheetCollectionType;
    fileSourcesConfigured: boolean;
    ftpUploadSite?: string;
    extendedCollectionType: ExtendedCollectionType;
    extensions?: string[];
}

async function handleUploadFromWizard(workbookContents: string) {
    workbookCompleted.value = true;
    await handleWorkbook(workbookContents);
    wizard.goTo("fill-grid");
}

const props = defineProps<Props>();

const sourceInstructions = computed(() => {
    return `Sample sheets can be initialized from a set or files, URIs, or existing collections of datasets.`;
});

async function handleWorkbook(base64Content: string) {
    const { data, error } = await parseWorkbook(
        props.collectionType,
        props.extendedCollectionType.columnDefinitions,
        prefixColumnsType.value,
        base64Content,
    );
    if (data) {
        parsedWorkbook.value = data;
    } else {
        console.log(error);
    }
}

// TODO: import and use uploadErrorMessage
const {
    browseFiles,
    dropZoneClasses,
    faUpload,
    FontAwesomeIcon,
    handleDrop,
    HiddenWorkbookUploadInput,
    isDragging,
    onFileUpload,
    uploadRef,
} = useWorkbookDropHandling(handleUploadFromWizard);

type UriForAutoPairing = { name: string; uri: string };

const { countPaired, currentForwardFilter, currentReverseFilter, AutoPairing, autoPair, onFilters, pairs, unpaired } =
    useAutoPairing<UriForAutoPairing>();

const sourceFrom = ref<RulesSourceFrom>("remote_files");
const prefixColumnsType = ref<PrefixColumnsType>("URI");
const parsedWorkbook = ref<AnyParsedSampleSheetWorkbook | undefined>(undefined);

function setSourceForm(newValue: RulesSourceFrom) {
    sourceFrom.value = newValue;
    if (sourceFrom.value == "collection") {
        prefixColumnsType.value = "ModelObjects";
    } else {
        prefixColumnsType.value = "URI";
    }
}

const columnDefinitions = computed(() => {
    return props.extendedCollectionType.columnDefinitions ?? [];
});

const targetCollectionId = ref<string | undefined>(undefined);
const targetCollection = ref<HDCADetailed | undefined>(undefined);

function resetElements() {
    parsedWorkbook.value = undefined;
}

function setTargetCollection(newValue: string) {
    resetElements();
    targetCollectionId.value = newValue;
}

const fetchingCollection = ref<boolean>(false);

watch(targetCollectionId, async () => {
    if (targetCollectionId.value) {
        fetchingCollection.value = true;
        try {
            // TODO: spinner while loading
            const details = await fetchCollectionDetails({ hdca_id: targetCollectionId.value });
            targetCollection.value = details;
            // Nothing else to do on the page, just skip to the next step.
            nextTick(() => {
                wizard.goTo("fill-grid");
            });
        } catch (error) {
            // TODO: proper error handling here.
            console.error("Error fetching collection details:", error);
        } finally {
            fetchingCollection.value = false;
        }
    }
});

const wizard = useWizard({
    "select-source": {
        label: "Select source",
        instructions: sourceInstructions,
        isValid: () => true,
        isSkippable: () => false,
    },
    "select-remote-files-folder": {
        label: "Select folder",
        instructions: "Select folder of files to import.",
        isValid: () => sourceFrom.value === "remote_files" && Boolean(uris.value.length > 0),
        isSkippable: () => sourceFrom.value !== "remote_files",
    },
    "paste-data": {
        label: "Paste data",
        instructions: "Paste data containing URIs and optional extra metadata.",
        isValid: () => sourceFrom.value === "pasted_table" && pasteData.value.length > 0,
        isSkippable: () => sourceFrom.value !== "pasted_table",
    },
    "select-dataset": {
        label: "Select dataset",
        instructions: "Select tabular dataset to load URIs and metadata from.",
        isValid: () => sourceFrom.value === "dataset_as_table" && tabularDatasetContents.value.length > 0,
        isSkippable: () => sourceFrom.value !== "dataset_as_table",
    },
    "select-collection": {
        label: "Select collection",
        instructions: "Select existing collection to transform into a sample sheet.",
        isValid: () => sourceFrom.value === "collection" && Boolean(targetCollection.value),
        isSkippable: () => sourceFrom.value !== "collection",
    },
    "auto-pairing": {
        label: "Auto Pairing",
        instructions: computed(() => {
            return "Configure auto-pairing";
        }),
        isValid: () => true,
        isSkippable: () => toAutoPair.value === undefined || allPaired.value,
    },
    "upload-workbook": {
        label: "Upload workbook",
        instructions: "Upload a workbook containing with URIs and metadata",
        isValid: () => sourceFrom.value === "workbook" && workbookCompleted.value,
        isSkippable: () => sourceFrom.value !== "workbook",
    },
    "fill-grid": {
        label: "Fill sheet",
        instructions: "Fill in metadata to describe the files you're importing.",
        isValid: () => true,
        isSkippable: () => false,
    },
});

const importButtonLabel = computed(() => {
    if (sourceFrom.value == "collection") {
        return "Build";
    } else {
        return "Import";
    }
});

const initialElements = computed<InitialElements>(() => {
    if (parsedWorkbook.value) {
        // just short cut all the rest - we have an upload with actual sample sheet data...
        return parsedWorkbook.value;
    } else {
        if (pairs.value) {
            // if we have pairs, we return them as initial elements.
            const rows: InitialElements = [];
            for (const pair of pairs.value) {
                rows.push([pair.forward.uri, pair.reverse.uri, pair.name]);
            }
            if (props.collectionType === "sample_sheet:paired_or_unpaired") {
                // if we have paired_or_unpaired collection, add the unpaired datasets as well.
                for (const unpaired_entry of unpaired.value ?? []) {
                    const identifier = stripExtension(guessUriFilename(unpaired_entry.uri));
                    rows.push([unpaired_entry.uri, "", identifier]);
                }
            }
            return rows;
        } else if (sourceFrom.value == "remote_files") {
            const rows: InitialElements = [];
            for (const uri of uris.value) {
                rows.push([uri.uri]);
            }
            return withAutoListIdentifiers(rows);
        } else if (sourceFrom.value == "pasted_table") {
            return withAutoListIdentifiers(pasteData.value) as InitialElements;
        } else if (sourceFrom.value == "dataset_as_table") {
            return withAutoListIdentifiers(tabularDatasetContents.value) as InitialElements;
        } else if (sourceFrom.value == "collection") {
            if (!targetCollection.value) {
                console.log("LOGIC ERROR: calling initial element for collection without collection contents fetched");
            } else {
                return targetCollection.value as InitialElements;
            }
        }
        return [];
    }
});

const pastedDataLooksPrePaired = computed(() => {
    // if the pasted data has a header row, we assume it is prepared for sample sheet.
    if (sourceFrom.value == "pasted_table") {
        const pastedData = pasteData.value;
        if (pastedData.length === 0) {
            return false;
        }
        for (const row of pastedData) {
            if (row.length !== 2) {
                return false; // we expect exactly two columns for each paired data.
            }
        }
        return true;
    } else {
        return false;
    }
});

function guessUriFilename(uri: string): string {
    const parts = uri.split("/");
    const last_part = parts[parts.length - 1] ?? uri;
    if (last_part.indexOf("?") !== -1) {
        // remove the query string
        return last_part.split("?")[0] as string;
    } else {
        return last_part;
    }
}

function adaptUriToAutoPair(uri: string): { name: string; uri: string } {
    return { name: guessUriFilename(uri), uri };
}

const toAutoPair = computed(() => {
    if (props.collectionType === "sample_sheet:paired" || props.collectionType === "sample_sheet:paired_or_unpaired") {
        if (pastedDataLooksPrePaired.value) {
            // don't auto-pair anything - the data was pasted in two clean columns - take it as is.
            return undefined;
        }
        if (sourceFrom.value == "pasted_table") {
            const uris: string[] = [];
            for (const row of pasteData.value) {
                uris.push(...row);
            }
            return uris.map(adaptUriToAutoPair);
        } else {
            return undefined;
        }
    } else {
        return undefined;
    }
});

const allPaired = computed<boolean>(() => {
    return !!(toAutoPair.value && countPaired.value === toAutoPair.value.length / 2);
});

watch(toAutoPair, (value) => {
    if (value !== undefined) {
        autoPair(value);
    }
});

const collectionCreator = ref<CollectionCreatorComponent>();

function submit() {
    if (collectionCreator.value) {
        attemptCreate(collectionCreator);
    }
}

const isSimpleSampleSheet = computed(() => {
    // we can do more with a simple list of URLs that don't need to be paired..
    return props.collectionType === "sample_sheet";
});

const waitingOnCollectionCreateApi = ref<boolean>(false);
const collectionCreateError = ref<string | undefined>(undefined);
const collectionCreated = ref<boolean>(false);

const { fetchAndWatch, fetchComplete, fetchError, waitingOnFetch } = useFetchJobMonitor();

async function onFetchTarget(fetchTarget: HdcaUploadTarget) {
    const fetchPayload: FetchDataPayload = {
        history_id: currentHistoryId.value as string,
        targets: [fetchTarget],
    };
    fetchAndWatch(fetchPayload);
}

watch(fetchComplete, (newValue) => {
    if (newValue) {
        collectionCreated.value = true;
    }
});

watch(fetchError, (newValue) => {
    if (newValue) {
        collectionCreateError.value = newValue;
    }
});

async function onCollectionCreatePayload(payload: CreateNewCollectionPayload) {
    waitingOnCollectionCreateApi.value = true;
    try {
        await createHistoryDatasetCollectionInstanceFull(payload);
        collectionCreated.value = true;
    } catch (error) {
        collectionCreateError.value = errorMessageAsString(error);
    }
    waitingOnCollectionCreateApi.value = false;
}

const wizardIsBusy = computed(() => {
    return (
        sourceIsBusy.value ||
        fetchingCollection.value ||
        waitingOnCollectionCreateApi.value ||
        waitingOnFetch.value ||
        collectionCreated.value
    );
});

async function download() {
    downloadWorkbook(props.extendedCollectionType.columnDefinitions!, props.collectionType);
}
</script>

<template>
    <GenericWizard :use="wizard" :is-busy="wizardIsBusy" :submit-button-label="importButtonLabel" @submit="submit">
        <div v-if="wizard.isCurrent('select-source')">
            <BCardGroup columns>
                <SourceFromRemoteFiles
                    v-if="isSimpleSampleSheet"
                    :selected="sourceFrom === 'remote_files'"
                    for-what="sample_sheet"
                    @select="setSourceForm" />
                <SourceFromPastedData
                    :selected="sourceFrom === 'pasted_table'"
                    for-what="sample_sheet"
                    @select="setSourceForm" />
                <SourceFromDatasetAsTable
                    v-if="isSimpleSampleSheet"
                    for-what="sample_sheet"
                    :selected="sourceFrom === 'dataset_as_table'"
                    @select="setSourceForm" />
                <SourceFromWorkbook
                    creating-what="collections"
                    :selected="sourceFrom === 'workbook'"
                    @select="setSourceForm" />
                <SourceFromCollection :selected="sourceFrom === 'collection'" @select="setSourceForm" />
            </BCardGroup>
        </div>
        <div v-else-if="wizard.isCurrent('paste-data')">
            <PasteData @onChange="setPasteTable" />
        </div>
        <div v-else-if="wizard.isCurrent('select-remote-files-folder')">
            <SelectFolder :ftp-upload-site="ftpUploadSite" @onChange="setRemoteFilesFolder" @onFtp="onFtp" />
        </div>
        <div v-else-if="wizard.isCurrent('select-dataset')">
            <SelectDataset @onChange="setDatasetContents" />
        </div>
        <div v-else-if="wizard.isCurrent('auto-pairing')">
            <AutoPairing
                v-if="collectionType === 'sample_sheet:paired' || collectionType === 'sample_sheet:paired_or_unpaired'"
                :elements="toAutoPair ?? []"
                :forward-filter="currentForwardFilter"
                :reverse-filter="currentReverseFilter"
                :collection-type="collectionType"
                :remove-extensions="true"
                :show-hid="false"
                mode="wizard"
                @on-update="onFilters" />
        </div>
        <div v-else-if="wizard.isCurrent('select-collection')">
            <SelectCollection
                :collection-type="collectionType"
                :extended-collection-type="extendedCollectionType"
                @onChange="setTargetCollection" />
        </div>
        <div v-else-if="wizard.isCurrent('upload-workbook')">
            <UploadSampleSheet
                :collection-type="collectionType"
                :extended-collection-type="extendedCollectionType"
                @download="download"
                @workbookContents="handleUploadFromWizard" />
        </div>
        <div v-else-if="wizard.isCurrent('fill-grid') && currentHistoryId" style="width: 100%">
            <BAlert v-if="collectionCreateError" show dismissible @dismissed="collectionCreateError = undefined">
                Failed to create sample sheet collection for supplied input. {{ collectionCreateError }}.
            </BAlert>
            <div v-if="collectionCreated">
                <BAlert variant="success" data-description="collection created" show
                    >Sample sheet collection successfully created!</BAlert
                >
            </div>
            <div v-else-if="waitingOnFetch">
                <LoadingSpan message="Waiting on data import job for sample sheet collection" />
            </div>
            <div v-else-if="waitingOnCollectionCreateApi">
                <LoadingSpan message="Creating sample sheet collection from supplied inputs" />
            </div>
            <SampleSheetGrid
                v-else-if="columnDefinitions"
                ref="collectionCreator"
                :current-history-id="currentHistoryId"
                :collection-type="collectionType"
                :column-definitions="columnDefinitions"
                :initial-elements="initialElements"
                :extensions="extensions"
                :busy="wizardIsBusy"
                height="300px"
                @workbook-contents="handleWorkbook"
                @on-fetch-target="onFetchTarget"
                @on-collection-create-payload="onCollectionCreatePayload" />
        </div>
        <div v-if="!wizard.isCurrent('fill-grid')" class="text-center">
            <div
                class="w-100 p-3 text-light"
                data-galaxy-file-drop-target
                :class="dropZoneClasses"
                @drop.prevent="handleDrop"
                @dragover.prevent="isDragging = true"
                @dragleave.prevent="isDragging = false">
                <BLink href="#" @click.prevent="browseFiles">
                    <FontAwesomeIcon size="xl" :icon="faUpload" />
                    Already have a completed workbook? Upload it here.
                </BLink>
                <HiddenWorkbookUploadInput ref="uploadRef" @onFileUpload="onFileUpload" />
            </div>
        </div>
    </GenericWizard>
</template>

<style scoped>
@import "@/components/Collections/wizard/workbook-dropzones.scss";

.dropzone {
    padding: 7px !important;
    width: 100%;
}
</style>
