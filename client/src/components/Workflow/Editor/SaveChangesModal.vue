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

const title = localize("您有未保存的更改。是否要在继续之前保存这些更改？");
const body = localize(
    "点击'保存'将保存您的更改并继续，'不保存'将丢弃更改并继续，或'取消'返回编辑器。"
);

const buttonTitles = {
    cancel: localize("不继续操作并返回编辑器"),
    dontSave: localize("丢弃更改并继续"),
    save: localize("保存更改并继续"),
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
                {{ localize("取消") }}
            </BButton>
            <BButton
                v-b-tooltip.noninteractive.hover
                :title="buttonTitles['dontSave']"
                variant="danger"
                :disabled="busy"
                @click="dontSave">
                <FontAwesomeIcon :icon="faTrash" />
                {{ localize("不保存") }}
            </BButton>
            <BButton
                v-b-tooltip.noninteractive.hover
                :title="buttonTitles['save']"
                variant="primary"
                :disabled="busy"
                @click="saveChanges">
                <FontAwesomeIcon :icon="faSave" />
                {{ localize("保存") }}
            </BButton>
        </template>
    </BModal>
</template>
