<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";

import { useWizard } from "@/components/Common/Wizard/useWizard";
import { useCollectionBuilderItemSelection } from "@/stores/collectionBuilderItemsStore";

import { type WhichListBuilder } from "./ListWizard/types";
import { autoPairWithCommonFilters } from "./pairing";

import ListCollectionCreator from "./ListCollectionCreator.vue";
import WhichBuilder from "./ListWizard/WhichBuilder.vue";
import PairedListCollectionCreator from "./PairedListCollectionCreator.vue";
import GenericWizard from "@/components/Common/Wizard/GenericWizard.vue";

const isBusy = ref<boolean>(false);
const whichBuilder = ref<WhichListBuilder>("list");
const store = useCollectionBuilderItemSelection();

const { selectedItems } = storeToRefs(store);

const countPaired = ref(-1);
const countUnpaired = ref(-1);
const inferredBuilder = ref<WhichListBuilder>("list");

async function initialize() {
    isBusy.value = true;
    const summary = autoPairWithCommonFilters(selectedItems.value, true);
    countPaired.value = summary.pairs?.length || 0;
    countUnpaired.value = summary.unpaired.length;
    if (countPaired.value * 2 > selectedItems.value.length * 0.2) {
        whichBuilder.value = "list:paired";
        inferredBuilder.value = "list:paired";
    } else {
        whichBuilder.value = "list";
        inferredBuilder.value = "list";
    }
    goToInferredBuilder();
    isBusy.value = false;
}

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
    "list-builder": {
        label: "Builder",
        instructions: computed(() => {
            return "Assemble, label, and sort your list.";
        }),
        isValid: () => true,
        isSkippable: () => whichBuilder.value !== "list",
    },
    "list-paired-builder": {
        label: "Builder",
        instructions: computed(() => {
            return "Assemble, label, and sort your list of pairs.";
        }),
        isValid: () => true,
        isSkippable: () => whichBuilder.value !== "list:paired",
    },
});

const buildButtonLabel = computed(() => {
    return "Build";
});

function submit() {
    console.log("submitted....");
}

function setWhichBuilder(newWhichBuilder: WhichListBuilder) {
    whichBuilder.value = newWhichBuilder;
}

function create() {
    console.log("in create...");
}
</script>

<template>
    <div>
        <GenericWizard :use="wizard" :is-busy="isBusy" :submit-button-label="buildButtonLabel" @submit="submit">
            <div v-if="wizard.isCurrent('which-builder')">
                <WhichBuilder :value="whichBuilder" @onChange="setWhichBuilder" />
            </div>
            <div v-else-if="wizard.isCurrent('list-builder')" class="collection-creator-bounded-help">
                <ListCollectionCreator
                    :history-id="'TODO'"
                    :initial-elements="selectedItems || []"
                    :default-hide-source-items="true"
                    :from-selection="true"
                    :show-upload="false"
                    :show-buttons="false"
                    @clicked-create="create" />
            </div>
            <div v-else-if="wizard.isCurrent('list-paired-builder')" class="collection-creator-bounded-help">
                <PairedListCollectionCreator
                    :history-id="'TODO'"
                    :initial-elements="selectedItems || []"
                    :default-hide-source-items="true"
                    :from-selection="true"
                    :show-upload="false"
                    :show-buttons="false"
                    @clicked-create="create" />
            </div>
        </GenericWizard>
    </div>
</template>
