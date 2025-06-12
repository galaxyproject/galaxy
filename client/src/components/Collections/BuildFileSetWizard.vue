<script setup lang="ts">
import { BCardGroup } from "bootstrap-vue";
import { computed, ref } from "vue";

import { getGalaxyInstance } from "@/app";
import { attemptCreate, type CollectionCreatorComponent } from "@/components/Collections/common/useCollectionCreator";
import { rawToTable } from "@/components/Collections/tables";
import { useWizard } from "@/components/Common/Wizard/useWizard";
import { useToolRouting } from "@/composables/route";
import localize from "@/utils/localization";

import type { RemoteFile, RulesCreatingWhat, RulesSourceFrom } from "./wizard/types";
import { useFileSetSources } from "./wizard/useFileSetSources";

import CreatingWhat from "./wizard/CreatingWhat.vue";
import PasteData from "./wizard/PasteData.vue";
import SelectDataset from "./wizard/SelectDataset.vue";
import SelectFolder from "./wizard/SelectFolder.vue";
import SourceFromCollectionApplyRules from "./wizard/SourceFromCollectionApplyRules.vue";
import SourceFromDatasetAsTable from "./wizard/SourceFromDatasetAsTable.vue";
import SourceFromPastedData from "./wizard/SourceFromPastedData.vue";
import SourceFromRemoteFiles from "./wizard/SourceFromRemoteFiles.vue";
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

const sourceFrom = ref<RulesSourceFrom>("remote_files");

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
type SelectionType = "raw" | "remote_files";
type ElementsType = RemoteFile[] | string[][];

// it would be nice to have a real type from the rule builder but
// it is older code. This is really outlining what this component can
// produce and not what the rule builder can consume which is a wide
// superset of this.
interface Entry {
    dataType: RulesCreatingWhat;
    ftpUploadSite?: string;
    elements?: ElementsType | undefined;
    content?: string;
    selectionType: SelectionType;
}

const ruleBuilderModalEntryProps = computed(() => {
    let elements: ElementsType | undefined = undefined;
    let selectionType: SelectionType = "raw";
    if (sourceFrom.value == "remote_files") {
        elements = uris.value;
        selectionType = "remote_files";
    } else if (sourceFrom.value == "pasted_table") {
        elements = pasteData.value;
    } else if (sourceFrom.value == "dataset_as_table") {
        elements = tabularDatasetContents.value;
    }
    const entry: Entry = {
        dataType: creatingWhat.value,
        ftpUploadSite: props.ftpUploadSite,
        selectionType: selectionType,
        elements: elements,
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

function onRuleState(newRuleState: boolean) {
    ruleState.value = newRuleState;
}

function onRuleCreate() {
    // axios response data for job currently sent, not really used but wanted to document what is available.
    emit("created");
}
</script>

<template>
    <GenericWizard :use="wizard" :submit-button-label="importButtonLabel" :title="title" @submit="submit">
        <div v-if="wizard.isCurrent('select-what')">
            <CreatingWhat :creating-what="creatingWhat" @onChange="setCreatingWhat" />
        </div>
        <div v-else-if="wizard.isCurrent('select-source')">
            <BCardGroup deck>
                <SourceFromRemoteFiles :selected="sourceFrom === 'remote_files'" @select="setSourceForm" />
                <SourceFromPastedData :selected="sourceFrom === 'pasted_table'" @select="setSourceForm" />
                <SourceFromDatasetAsTable :selected="sourceFrom === 'dataset_as_table'" @select="setSourceForm" />
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
        <div v-else-if="wizard.isCurrent('rule-builder')" style="width: 100%">
            <RuleCollectionBuilder
                ref="collectionCreator"
                grid-implementation="ag"
                :import-type="creatingWhat"
                :elements-type="ruleBuilderModalEntryProps.selectionType"
                :initial-elements="ruleBuilderElements"
                mode="wizard"
                @onCreate="onRuleCreate"
                @validInput="onRuleState" />
        </div>
    </GenericWizard>
</template>
