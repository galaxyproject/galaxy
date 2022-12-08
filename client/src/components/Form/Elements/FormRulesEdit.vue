<script setup>
import RuleCollectionBuilder from "components/RuleCollectionBuilder";
import RulesDisplay from "components/RulesDisplay/RulesDisplay";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref, computed } from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

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

const initialRules = {
    rules: [],
    mapping: [],
};

const displayRules = computed(() => props.value ?? initialRules);

async function onEdit() {
    if (props.target) {
        const url = `${getAppRoot()}api/dataset_collections/${props.target.id}?instance_type=history`;

        try {
            const response = await axios.get(url);
            elements.value = response.data;
            modal.value.show();
        } catch (e) {
            console.error(e);
            console.log("problem fetching collection");
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

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEdit } from "@fortawesome/free-solid-svg-icons";

library.add(faEdit);
</script>

<template>
    <div class="form-rules-edit">
        <RulesDisplay :input-rules="displayRules" />
        <b-button title="Edit Rules" @click="onEdit">
            <FontAwesomeIcon icon="fa-edit" />
            <span>Edit</span>
        </b-button>

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
