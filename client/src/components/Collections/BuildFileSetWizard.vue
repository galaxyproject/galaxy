<script setup lang="ts">
import { BCardGroup } from "bootstrap-vue";
import { computed, ref } from "vue";

import { GalaxyApi } from "@/api";
import { getGalaxyInstance } from "@/app";
import { attemptCreate, type CollectionCreatorComponent } from "@/components/Collections/common/useCollectionCreator";
import { useWorkbookDropHandling } from "@/components/Collections/common/useWorkbooks";
import { rawToTable } from "@/components/Collections/tables";
import { forBuilder, type ForBuilderResponse } from "@/components/Collections/wizard/fetchWorkbooks";
import { useWizard } from "@/components/Common/Wizard/useWizard";
import { useToolRouting } from "@/composables/route";
import localize from "@/utils/localization";

import type {
    ParsedFetchWorkbook,
    ParsedFetchWorkbookForCollectionCollectionType,
    RuleBuilderMapping,
    RuleBuilderOptions,
    RuleElementsType,
    RulesCreatingWhat,
    RuleSelectionType,
    RulesSourceFrom,
} from "./wizard/types";
import { useFileSetSources } from "./wizard/useFileSetSources";

import ConfigureFetchWorkbook from "./wizard/ConfigureFetchWorkbook.vue";
import CreatingWhat from "./wizard/CreatingWhat.vue";
import PasteData from "./wizard/PasteData.vue";
import SelectDataset from "./wizard/SelectDataset.vue";
import SelectFolder from "./wizard/SelectFolder.vue";
import SourceFromCollectionApplyRules from "./wizard/SourceFromCollectionApplyRules.vue";
import SourceFromDatasetAsTable from "./wizard/SourceFromDatasetAsTable.vue";
import SourceFromPastedData from "./wizard/SourceFromPastedData.vue";
import SourceFromRemoteFiles from "./wizard/SourceFromRemoteFiles.vue";
import SourceFromWorkbook from "./wizard/SourceFromWorkbook.vue";
import UploadFetchWorkbook from "./wizard/UploadFetchWorkbook.vue";
import GenericWizard from "@/components/Common/Wizard/GenericWizard.vue";
import RuleCollectionBuilder from "@/components/RuleCollectionBuilder.vue";

const isBusy = ref<boolean>(false);
const { pasteData, tabularDatasetContents, uris, setRemoteFilesFolder, onFtp, setDatasetContents, setPasteTable } =
    useFileSetSources(isBusy);

interface Props {
    fileSourcesConfigured: boolean;
    ftpUploadSite?: string;
    mode: "uploadModal" | "standalone";
}

const props = defineProps<Props>();

const title = localize("Rule Based Data Import");
const ruleState = ref(false);
const creatingWhat = ref<RulesCreatingWhat>("datasets");
const creatingWhatTitle = computed(() => {
    return creatingWhat.value == "datasets" ? "Datasets" : "Collections";
});
const sourceInstructions = computed(() => {
    return `${creatingWhatTitle.value} can be created from a set or files, URIs, or existing datasets.`;
});
const collectionCreator = ref<CollectionCreatorComponent | undefined>();
const workbookCompleted = ref<boolean>(false);
// workbook generation options
const workbookCollectionType = ref<ParsedFetchWorkbookForCollectionCollectionType>("list");
const workbookIncludeCollectionName = ref<boolean>(false);

const sourceFrom = ref<RulesSourceFrom>("remote_files");
// if we upload a workbook - just jump to the end with these properties
const parsedWorkbookUploadProps = ref<ForBuilderResponse | undefined>(undefined);

const { routeToTool } = useToolRouting();

const wizard = useWizard({
    "select-what": {
        label: "What is being created?",
        instructions: computed(() => {
            return `Are you creating datasets or collections?`;
        }),
        isValid: () => true,
        isSkippable: () => false,
    },
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
        instructions: "Paste data (or drop file) containing URIs and optional extra metadata.",
        isValid: () => sourceFrom.value === "pasted_table" && pasteData.value.length > 0,
        isSkippable: () => sourceFrom.value !== "pasted_table",
    },
    "select-dataset": {
        label: "Select dataset",
        instructions: "Select tabular dataset to load URIs and metadata from.",
        isValid: () => sourceFrom.value === "dataset_as_table" && tabularDatasetContents.value.length > 0,
        isSkippable: () => sourceFrom.value !== "dataset_as_table",
    },
    "configure-workbook": {
        label: "Configure workbook",
        instructions: "Configure a workbook to fill with URIs and metadata",
        isValid: () => sourceFrom.value === "workbook" && workbookCollectionType.value !== undefined,
        isSkippable: () => sourceFrom.value !== "workbook" || creatingWhat.value !== "collections",
    },
    "upload-workbook": {
        label: "Upload workbook",
        instructions: "Upload a workbook containing with URIs and metadata",
        isValid: () => sourceFrom.value === "workbook" && workbookCompleted.value,
        isSkippable: () => sourceFrom.value !== "workbook",
    },
    "rule-builder": {
        label: "Specify Rules",
        instructions: "Use this form to describe rules for importing",
        isValid: () => ruleState.value,
        isSkippable: () => props.mode == "uploadModal",
        width: "100%",
    },
});

const importButtonLabel = computed(() => {
    if (sourceFrom.value == "collection") {
        return "Transform";
    } else {
        return "Import";
    }
});

const emit = defineEmits(["dismiss", "created"]);

const ruleBuilderModalEntryProps = computed(() => {
    let elements: RuleElementsType | undefined = undefined;
    let initialMappings: RuleBuilderMapping | undefined = undefined;
    let selectionType: RuleSelectionType = "raw";
    if (parsedWorkbookUploadProps.value) {
        elements = parsedWorkbookUploadProps.value.initialElements;
        initialMappings = parsedWorkbookUploadProps.value.initialMapping;
    } else if (sourceFrom.value == "remote_files") {
        elements = uris.value;
        selectionType = "remote_files";
    } else if (sourceFrom.value == "pasted_table") {
        elements = pasteData.value;
    } else if (sourceFrom.value == "dataset_as_table") {
        elements = tabularDatasetContents.value;
    }
    const entry: RuleBuilderOptions = {
        dataType: creatingWhat.value,
        ftpUploadSite: props.ftpUploadSite,
        selectionType: selectionType,
        elements: elements,
        initialMappings: initialMappings,
    };
    return entry;
});

const ruleBuilderElements = computed(() => {
    const builderProps = ruleBuilderModalEntryProps.value;
    let elements;
    if (builderProps.elements) {
        elements = builderProps.elements;
    } else {
        elements = rawToTable(builderProps.content || "");
    }
    return elements;
});

function launchRuleBuilder() {
    const Galaxy = getGalaxyInstance();
    const entry = ruleBuilderModalEntryProps.value;
    Galaxy.currHistoryPanel.buildCollectionFromRules(entry, null, true);
}

function submit() {
    if (sourceFrom.value == "collection") {
        routeToTool("__APPLY_RULES__");
    } else if (props.mode == "standalone") {
        attemptCreate(collectionCreator);
    } else {
        launchRuleBuilder();
    }
    emit("dismiss");
}

function setCreatingWhat(what: RulesCreatingWhat) {
    creatingWhat.value = what;
}

function setSourceForm(newValue: RulesSourceFrom) {
    sourceFrom.value = newValue;
}

function setWorkbookCollectionType(newValue: ParsedFetchWorkbookForCollectionCollectionType) {
    workbookCollectionType.value = newValue;
}

function setWorkbookIncludeCollectionName(newValue: boolean) {
    workbookIncludeCollectionName.value = newValue;
}

function onRuleState(newRuleState: boolean) {
    ruleState.value = newRuleState;
}

function onRuleCreate() {
    // axios response data for job currently sent, not really used but wanted to document what is available.
    emit("created");
}

const dropWorkbookTitle = computed(() => {
    return localize(
        "If you have a completed data import workbook just drop it here or click this icon to upload your local file and skip ahead to the end of the data import wizard."
    );
});

function handleUploadedData(response: ParsedFetchWorkbook) {
    sourceFrom.value = "workbook";
    const builderPropsFromUpload = forBuilder(response);
    creatingWhat.value = builderPropsFromUpload.rulesCreatingWhat;
    parsedWorkbookUploadProps.value = builderPropsFromUpload;
    workbookCompleted.value = true;
    wizard.goTo("rule-builder");
}

async function handleWorkbook(base64Content: string) {
    const parseBody = {
        content: base64Content,
    };
    const { data, error } = await GalaxyApi().POST("/api/tools/fetch/workbook/parse", {
        body: parseBody,
    });
    if (data) {
        handleUploadedData(data);
    } else {
        console.log(error);
        uploadErrorMessage.value = "There was an error processing the file.";
    }
}

const {
    browseFiles,
    dropZoneClasses,
    faUpload,
    FontAwesomeIcon,
    handleDrop,
    HiddenWorkbookUploadInput,
    isDragging,
    onFileUpload,
    uploadErrorMessage,
    uploadRef,
} = useWorkbookDropHandling(handleWorkbook);
</script>

<template>
    <GenericWizard :use="wizard" :submit-button-label="importButtonLabel" :title="title" @submit="submit">
        <template v-slot:header>
            <h2 data-galaxy-file-drop-target>
                {{ title }}
                <FontAwesomeIcon
                    class="workbook-upload-helper mr-1"
                    :class="dropZoneClasses"
                    :title="dropWorkbookTitle"
                    :icon="faUpload"
                    @click.prevent="browseFiles"
                    @drop.prevent="handleDrop"
                    @dragover.prevent="isDragging = true"
                    @dragleave.prevent="isDragging = false" />
                <HiddenWorkbookUploadInput ref="uploadRef" @onFileUpload="onFileUpload" />
            </h2>
        </template>
        <div v-if="wizard.isCurrent('select-what')">
            <CreatingWhat :creating-what="creatingWhat" @onChange="setCreatingWhat" />
        </div>
        <div v-else-if="wizard.isCurrent('select-source')">
            <BCardGroup deck>
                <SourceFromRemoteFiles :selected="sourceFrom === 'remote_files'" @select="setSourceForm" />
                <SourceFromPastedData :selected="sourceFrom === 'pasted_table'" @select="setSourceForm" />
                <SourceFromDatasetAsTable :selected="sourceFrom === 'dataset_as_table'" @select="setSourceForm" />
                <SourceFromWorkbook
                    :creating-what="creatingWhat"
                    :selected="sourceFrom === 'workbook'"
                    @select="setSourceForm" />
                <SourceFromCollectionApplyRules
                    v-if="creatingWhat == 'collections'"
                    :selected="sourceFrom === 'collection'"
                    @select="setSourceForm" />
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
        <div v-else-if="wizard.isCurrent('configure-workbook')">
            <ConfigureFetchWorkbook
                :collection-type="workbookCollectionType"
                :include-collection-name="workbookIncludeCollectionName"
                @onCollectionType="setWorkbookCollectionType"
                @onIncludeCollectionName="setWorkbookIncludeCollectionName" />
        </div>
        <div v-else-if="wizard.isCurrent('upload-workbook')">
            <UploadFetchWorkbook
                :creating-what="creatingWhat"
                :collection-type="workbookCollectionType"
                :include-collection-name="workbookIncludeCollectionName"
                @workbookContents="handleWorkbook" />
        </div>
        <div v-else-if="wizard.isCurrent('rule-builder')" style="width: 100%">
            <RuleCollectionBuilder
                ref="collectionCreator"
                grid-implementation="ag"
                :import-type="creatingWhat"
                :elements-type="ruleBuilderModalEntryProps.selectionType"
                :initial-elements="ruleBuilderElements"
                :initial-mapping="ruleBuilderModalEntryProps.initialMappings"
                mode="wizard"
                @onCreate="onRuleCreate"
                @validInput="onRuleState" />
        </div>
    </GenericWizard>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";
@import "@/components/Collections/wizard/workbook-dropzones.scss";

// modeled a bit after upload-helper in the upload component...
.workbook-upload-helper {
    color: $border-color;
}
</style>
