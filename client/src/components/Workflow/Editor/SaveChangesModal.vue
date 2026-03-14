<script setup lang="ts">
import { faSave, faTimes, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import localize from "@/utils/localization";

import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

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
    "Click 'Save' to save your changes and proceed, 'Don't Save' to discard them and proceed, or 'Cancel' to return to the editor.",
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
    <GModal footer :title="title" size="small" :show="props.showModal" @close="closeModal">
        <div>
            {{ body }}
        </div>
        <template v-slot:footer>
            <div class="save-changes-modal-button-container">
                <GButton tooltip :title="buttonTitles['cancel']" :disabled="busy" @click="closeModal">
                    <FontAwesomeIcon :icon="faTimes" />
                    {{ localize("Cancel") }}
                </GButton>
                <GButton tooltip :title="buttonTitles['dontSave']" color="red" :disabled="busy" @click="dontSave">
                    <FontAwesomeIcon :icon="faTrash" />
                    {{ localize("Don't Save") }}
                </GButton>
                <GButton tooltip :title="buttonTitles['save']" color="blue" :disabled="busy" @click="saveChanges">
                    <FontAwesomeIcon :icon="faSave" />
                    {{ localize("Save") }}
                </GButton>
            </div>
        </template>
    </GModal>
</template>

<style scoped lang="scss">
.save-changes-modal-button-container {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-2);
}
</style>
