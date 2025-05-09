<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";

import type { CollectionElementIdentifiers, CreateNewCollectionPayload } from "@/api";
import { createHistoryDatasetCollectionInstanceFull } from "@/api/datasetCollections";
import { useWizard } from "@/components/Common/Wizard/useWizard";
import { useCollectionBuilderItemSelection } from "@/stores/collectionBuilderItemsStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { useCollectionCreation } from "./common/useCollectionCreation";
import {
    attemptCreate,
    type CollectionCreatorComponent,
    type SupportedPairedOrPairedBuilderCollectionTypes,
} from "./common/useCollectionCreator";
import { showHid } from "./common/useCollectionCreator";
import { type WhichListBuilder } from "./ListWizard/types";
import { autoPairWithCommonFilters } from "./pairing";

import AutoPairing from "./common/AutoPairing.vue";
import ListCollectionCreator from "./ListCollectionCreator.vue";
import WhichBuilder from "./ListWizard/WhichBuilder.vue";
import PairedOrUnpairedListCollectionCreator from "./PairedOrUnpairedListCollectionCreator.vue";
import GenericWizard from "@/components/Common/Wizard/GenericWizard.vue";
import RuleCollectionBuilder from "components/RuleCollectionBuilder.vue";

interface Props {
    initialAdvanced: boolean;
}

const props = defineProps<Props>();

const isBusy = ref<boolean>(false);
const whichBuilder = ref<WhichListBuilder>("list");
const store = useCollectionBuilderItemSelection();
const { currentHistoryId, createPayload } = useCollectionCreation();
const currentForwardFilter = ref("");
const currentReverseFilter = ref("");
const creationError = ref<string | null>(null);
const collectionCreated = ref(false);

type InferrableBuilder = "list" | "list:paired";
const collectionCreator = ref<CollectionCreatorComponent>();
const { selectedItems } = storeToRefs(store);

const countPaired = ref(-1);
const countUnpaired = ref(-1);
const inferredBuilder = ref<InferrableBuilder>("list");
const builderInputsValid = ref(false);

async function initialize() {
    isBusy.value = true;
    const summary = autoPairWithCommonFilters(selectedItems.value, true);
    currentForwardFilter.value = summary.forwardFilter || "";
    currentReverseFilter.value = summary.reverseFilter || "";
    countPaired.value = summary.pairs?.length || 0;
    countUnpaired.value = summary.unpaired.length;
    if (countPaired.value * 2 > selectedItems.value.length * 0.2) {
        whichBuilder.value = "list:paired";
        inferredBuilder.value = "list:paired";
    } else {
        whichBuilder.value = "list";
        inferredBuilder.value = "list";
    }

    if (!props.initialAdvanced) {
        goToInferredBuilder();
    }
    isBusy.value = false;
}

const requiresPairing = computed(() => {
    return whichBuilder.value === "list:paired" || whichBuilder.value == "list:paired_or_unpaired";
});

function goToInferredBuilder() {
    const builder = inferredBuilder.value;
    if (builder == "list") {
        wizard.goTo("list-builder");
    } else if (builder == "list:paired") {
        wizard.goTo("list-paired-builder");
    }
}

watch(selectedItems, () => {
    initialize();
});

const instructions = computed(() => {
    if (whichBuilder.value == "list") {
        return "Assemble, label, and sort your list.";
    } else if (whichBuilder.value == "list:paired") {
        return "Assemble, label, and sort your list of pairs.";
    } else if (whichBuilder.value == "list:paired_or_unpaired") {
        return "Assemble, label, and sort your list of paired and unpaired datasets.";
    } else {
        return "Assemble, label, and sort your list.";
    }
});

onMounted(initialize);

const wizard = useWizard({
    "which-builder": {
        label: "What are you building?",
        instructions: computed(() => {
            return `Choose a list builder to match your selected data and the kind of list you'd like to build.`;
        }),
        isValid: () => true,
        isSkippable: () => false,
    },
    "auto-pairing": {
        label: "Auto Pairing",
        instructions: computed(() => {
            return "Configure auto-pairing";
        }),
        isValid: () => true,
        isSkippable: () => !requiresPairing.value,
    },
    "list-builder": {
        label: "Builder",
        instructions: instructions,
        isValid: () => builderInputsValid.value,
        isSkippable: () => whichBuilder.value !== "list",
    },
    "list-paired-builder": {
        label: "Builder",
        instructions: instructions,
        isValid: () => builderInputsValid.value,
        isSkippable: () => ["list", "rules"].indexOf(whichBuilder.value) !== -1,
    },
    rules: {
        label: "Builder",
        instructions: computed(() => {
            return "Assemble, label, and sort your list(s).";
        }),
        isValid: () => ruleState.value,
        isSkippable: () => whichBuilder.value !== "rules",
    },
});

const collectionTypeForPairedOrUnpairedBuilder = computed(
    () => whichBuilder.value as SupportedPairedOrPairedBuilderCollectionTypes
);

const buildButtonLabel = computed(() => {
    return "Build";
});

const pairedListType = computed(() => {
    return whichBuilder.value == "list:paired_or_unpaired" ? "list:paired_or_unpaired" : "list:paired";
});

async function submit() {
    if (collectionCreator.value) {
        attemptCreate(collectionCreator);
    }
}

async function onCreate(payload: CreateNewCollectionPayload) {
    try {
        await createHistoryDatasetCollectionInstanceFull(payload);
        collectionCreated.value = true;
    } catch (e) {
        creationError.value = errorMessageAsString(e);
    }
}

type RuleCreationRequestT = {
    name: string;
    collectionType: string;
    elementIdentifiers: CollectionElementIdentifiers;
    hide_source_items: boolean;
}[];

async function ruleOnAttemptCreate(createRequest: RuleCreationRequestT) {
    for (const request of createRequest) {
        const payload = createPayload(
            request.name,
            request.collectionType,
            request.elementIdentifiers,
            request.hide_source_items
        );
        await onCreate(payload);
    }
}

function setWhichBuilder(newWhichBuilder: WhichListBuilder) {
    whichBuilder.value = newWhichBuilder;
}

function onFilters(forwardFilter: string, reverseFilter: string) {
    currentForwardFilter.value = forwardFilter;
    currentReverseFilter.value = reverseFilter;
}

function goToAutoPairing() {
    wizard.goTo("auto-pairing");
}

const ruleState = ref(false);

function onRuleState(newRuleState: boolean) {
    ruleState.value = newRuleState;
}
</script>

<template>
    <div v-if="currentHistoryId">
        <div v-if="creationError">
            <BAlert variant="danger">
                {{ creationError }}
            </BAlert>
        </div>
        <div v-if="collectionCreated">
            <BAlert variant="success" show> Collection created and it has been added to your history. </BAlert>
        </div>
        <div v-else-if="!selectedItems">Loading...</div>
        <div v-else-if="selectedItems.length == 0">
            <p>Select datasets from history panel to use the Galaxy list building wizard.</p>
        </div>
        <GenericWizard v-else :use="wizard" :is-busy="isBusy" :submit-button-label="buildButtonLabel" @submit="submit">
            <div v-if="wizard.isCurrent('which-builder')">
                <WhichBuilder :initial-advanced="initialAdvanced" :value="whichBuilder" @onChange="setWhichBuilder" />
            </div>
            <div v-else-if="wizard.isCurrent('list-builder')" class="collection-creator-bounded-help">
                <ListCollectionCreator
                    ref="collectionCreator"
                    :history-id="currentHistoryId"
                    :initial-elements="selectedItems || []"
                    :default-hide-source-items="true"
                    :from-selection="true"
                    :show-upload="false"
                    mode="wizard"
                    @input-valid="(e) => (builderInputsValid = e)"
                    @on-create="onCreate" />
            </div>
            <div v-else-if="wizard.isCurrent('auto-pairing')">
                <AutoPairing
                    :elements="selectedItems || []"
                    :forward-filter="currentForwardFilter"
                    :reverse-filter="currentReverseFilter"
                    :collection-type="pairedListType"
                    :remove-extensions="true"
                    :show-hid="showHid"
                    mode="wizard"
                    @on-update="onFilters" />
            </div>
            <div v-else-if="wizard.isCurrent('list-paired-builder')">
                <PairedOrUnpairedListCollectionCreator
                    ref="collectionCreator"
                    :history-id="currentHistoryId"
                    :initial-elements="selectedItems || []"
                    :collection-type="collectionTypeForPairedOrUnpairedBuilder"
                    mode="wizard"
                    :default-hide-source-items="true"
                    :from-selection="true"
                    :show-upload="false"
                    :show-buttons="false"
                    @input-valid="(e) => (builderInputsValid = e)"
                    @go-to-auto-pairing="goToAutoPairing"
                    @on-create="onCreate" />
            </div>
            <div v-else-if="wizard.isCurrent('rules')">
                <RuleCollectionBuilder
                    ref="collectionCreator"
                    grid-implementation="ag"
                    import-type="collections"
                    elements-type="datasets"
                    :initial-elements="selectedItems || []"
                    mode="wizard"
                    @onAttemptCreate="ruleOnAttemptCreate"
                    @validInput="onRuleState" />
            </div>
        </GenericWizard>
    </div>
</template>
