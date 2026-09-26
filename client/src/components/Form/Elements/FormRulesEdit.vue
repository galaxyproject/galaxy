<script setup lang="ts">
import { faEdit } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

import type { HDCADetailed } from "@/api";
import { fetchCollectionDetails } from "@/api/datasetCollections";
import { errorMessageAsString } from "@/utils/simple-error";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import RuleCollectionBuilder from "@/components/RuleCollectionBuilder.vue";
import RulesDisplay from "@/components/RulesDisplay/RulesDisplay.vue";

interface Rules {
    rules: any[];
    mapping: any[];
}

interface Props {
    id: string;
    value?: Rules;
    target?: { id: string } | null;
}

const props = withDefaults(defineProps<Props>(), {
    value: undefined,
    target: null,
});

const elements = ref<HDCADetailed | null>(null);
const showModal = ref(false);
const loading = ref(false);
const loadError = ref<string | undefined>(undefined);

const initialRules: Rules = {
    rules: [],
    mapping: [],
};

const displayRules = computed(() => props.value ?? initialRules);

async function onEdit() {
    if (props.target) {
        try {
            loading.value = true;
            loadError.value = undefined;
            const result = await fetchCollectionDetails({ hdca_id: props.target.id });
            if (result.error) {
                throw result.error;
            }
            elements.value = result.data;
            showModal.value = true;
        } catch (e) {
            loadError.value = errorMessageAsString(e);
        } finally {
            loading.value = false;
        }
    } else {
        showModal.value = true;
    }
}

const emit = defineEmits(["input"]);

function onSaveRules(rules: Rules) {
    showModal.value = false;
    emit("input", rules);
}

function onCancel() {
    showModal.value = false;
}
</script>

<template>
    <div class="form-rules-edit">
        <RulesDisplay :input-rules="displayRules" />
        <GButton :id="props.id" title="Edit Rules" @click="onEdit">
            <FontAwesomeIcon :icon="faEdit" />
            <span>Edit</span>
        </GButton>
        <LoadingSpan v-if="loading" message="Loading collection details" />
        <GAlert v-if="loadError" variant="danger" dismissible @dismissed="loadError = undefined">
            {{ loadError }}
        </GAlert>
        <GModal :show.sync="showModal" title="Build Rules for Applying to Existing Collection" size="medium">
            <!-- Note: We need the v-if="showModal" here because the rules do not appear inline with 
            the table otherwise. -->
            <RuleCollectionBuilder
                v-if="showModal"
                elements-type="collection_contents"
                import-type="collections"
                :initial-elements="elements"
                :initial-rules="props.value"
                :save-rules-fn="onSaveRules"
                :oncancel="onCancel"
                :oncreate="() => {}" />
        </GModal>
    </div>
</template>
