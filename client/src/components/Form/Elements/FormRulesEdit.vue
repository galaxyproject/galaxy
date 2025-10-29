<script setup>
import { faEdit } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, ref } from "vue";

import { fetchCollectionDetails } from "@/api/datasetCollections";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import RuleCollectionBuilder from "@/components/RuleCollectionBuilder.vue";
import RulesDisplay from "@/components/RulesDisplay/RulesDisplay.vue";

const props = defineProps({
    value: {
        type: Object,
    },
    target: {
        type: Object,
        default: null,
    },
});

const modal = ref(null);
const elements = ref(null);
const loading = ref(false);
const loadError = ref();

const initialRules = {
    rules: [],
    mapping: [],
};

const displayRules = computed(() => props.value ?? initialRules);

async function onEdit() {
    if (props.target) {
        try {
            loading.value = true;
            loadError.value = undefined;
            const collectionDetails = await fetchCollectionDetails({ hdca_id: props.target.id });
            elements.value = collectionDetails;
            modal.value.show();
        } catch (e) {
            loadError.value = errorMessageAsString(e);
            console.error(e);
            console.log("problem fetching collection");
        } finally {
            loading.value = false;
        }
    } else {
        modal.value.show();
    }
}

const emit = defineEmits(["input"]);

function onSaveRules(rules) {
    modal.value.hide();
    emit("input", rules);
}

function onCancel() {
    modal.value.hide();
}
</script>

<template>
    <div class="form-rules-edit">
        <RulesDisplay :input-rules="displayRules" />
        <GButton title="Edit Rules" @click="onEdit">
            <FontAwesomeIcon :icon="faEdit" />
            <span>Edit</span>
        </GButton>
        <LoadingSpan v-if="loading" message="Loading collection details"> </LoadingSpan>
        <BAlert v-if="loadError" show variant="danger" dismissible @dismissed="loadError = undefined">
            {{ loadError }}
        </BAlert>
        <b-modal ref="modal" modal-class="ui-form-rules-edit-modal" hide-footer>
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
        </b-modal>
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
