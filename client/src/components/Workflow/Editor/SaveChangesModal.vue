<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faSave, faTimes, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BModal } from "bootstrap-vue";
import { ref } from "vue";

import localize from "@/utils/localization";

library.add(faSave, faTimes, faTrash);

interface Props {
    /** Show the save changes modal */
    showModal: boolean;
    /** The URL to navigate to before saving/ignoring changes */
    navUrl: string;
}

const props = withDefaults(defineProps<Props>(), {
    showModal: false,
});

const busy = ref(false);

const emit = defineEmits<{
    /** Proceed with or without saving the changes */
    (e: "on-proceed", url: string, forceSave: boolean, ignoreChanges: boolean, appendVersion: boolean): void;
    /** Update the nav URL prop */
    (e: "update:nav-url", url: string): void;
    /** Update the show modal boolean prop */
    (e: "update:show-modal", showModal: boolean): void;
}>();

const title = localize("You have unsaved changes. Do you want to save them before proceeding?");
const body = localize(
    "Click 'Save' to save your changes and proceed, 'Don't Save' to discard them and proceed, or 'Cancel' to return to the editor."
);

const buttonTitles = {
    cancel: localize("Do not run proceed and return to editor"),
    dontSave: localize("Discard changes and proceed"),
    save: localize("Save changes and proceed"),
};

function closeModal() {
    emit("update:show-modal", false);
    emit("update:nav-url", "");
}

function dontSave() {
    busy.value = true;
    emit("on-proceed", props.navUrl, false, true, true);
}

function saveChanges() {
    busy.value = true;
    closeModal();
    emit("on-proceed", props.navUrl, true, false, true);
}
</script>

<template>
    <BModal :title="title" :visible="props.showModal" @close="closeModal" @hide="closeModal">
        <div>
            {{ body }}
        </div>
        <template v-slot:modal-footer>
            <BButton
                v-b-tooltip.noninteractive.hover
                :title="buttonTitles['cancel']"
                variant="secondary"
                :disabled="busy"
                @click="closeModal">
                <FontAwesomeIcon :icon="faTimes" />
                {{ localize("Cancel") }}
            </BButton>
            <BButton
                v-b-tooltip.noninteractive.hover
                :title="buttonTitles['dontSave']"
                variant="danger"
                :disabled="busy"
                @click="dontSave">
                <FontAwesomeIcon :icon="faTrash" />
                {{ localize("Don't Save") }}
            </BButton>
            <BButton
                v-b-tooltip.noninteractive.hover
                :title="buttonTitles['save']"
                variant="primary"
                :disabled="busy"
                @click="saveChanges">
                <FontAwesomeIcon :icon="faSave" />
                {{ localize("Save") }}
            </BButton>
        </template>
    </BModal>
</template>
