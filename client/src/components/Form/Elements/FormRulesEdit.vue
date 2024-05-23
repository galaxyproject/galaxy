<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEdit } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BModal } from "bootstrap-vue";
import { computed, ref } from "vue";

import { type HDCADetailed } from "@/api";
import { fetchCollectionDetails } from "@/api/datasetCollections";

import RuleCollectionBuilder from "@/components/RuleCollectionBuilder.vue";
import RulesDisplay from "@/components/RulesDisplay/RulesDisplay.vue";

library.add(faEdit);

interface Props {
    value: {
        rules: any[];
        mapping: any[];
    };
    target: {
        id: string;
    };
}

const props = defineProps<Props>();

const emit = defineEmits<{
    // TODO: Define the correct type for the value
    (e: "input", value: any): void;
}>();

const modal = ref<BModal>();
const elements = ref<HDCADetailed>();

const initialRules = {
    rules: [],
    mapping: [],
};

const displayRules = computed(() => props.value ?? initialRules);

async function onEdit() {
    if (props.target) {
        try {
            const collectionDetails = await fetchCollectionDetails({ id: props.target.id });

            elements.value = collectionDetails;

            modal.value?.show();
        } catch (e) {
            console.error(e);
            console.log("problem fetching collection");
        }
    } else {
        modal.value?.show();
    }
}

// TODO: Define the correct type for the rules
function onSaveRules(rules: any) {
    modal.value?.hide();

    emit("input", rules);
}

function onCancel() {
    modal.value?.hide();
}
</script>

<template>
    <div class="form-rules-edit">
        <RulesDisplay :input-rules="displayRules" />

        <BButton title="Edit Rules" @click="onEdit">
            <FontAwesomeIcon :icon="faEdit" />

            <span>Edit</span>
        </BButton>

        <BModal ref="modal" modal-class="ui-form-rules-edit-modal" hide-footer>
            <template v-slot:modal-title>
                <h2 class="mb-0">Build Rules for Applying to Existing Collection</h2>
            </template>

            <RuleCollectionBuilder
                elements-type="collection_contents"
                import-type="collections"
                :initial-elements="elements"
                :initial-rules="props.value"
                :save-rules-fn="onSaveRules"
                :oncancel="onCancel"
                :oncreate="() => {}" />
        </BModal>
    </div>
</template>

<style lang="scss">
.ui-form-rules-edit-modal {
    .modal-dialog {
        width: 100%;
        max-width: 85%;
    }
}
</style>
