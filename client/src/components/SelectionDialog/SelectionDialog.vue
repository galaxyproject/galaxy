<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretLeft, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BModal } from "bootstrap-vue";

library.add(faCaretLeft, faSpinner);

interface Props {
    backFunc?: () => void;
    disableOk?: boolean;
    errorMessage?: string;
    fileMode?: boolean;
    hideModal?: () => void;
    modalShow?: boolean;
    modalStatic?: boolean;
    multiple?: boolean;
    onOk?: () => void;
    optionsShow?: boolean;
    undoShow?: boolean;
}

withDefaults(defineProps<Props>(), {
    backFunc: () => {},
    disableOk: false,
    errorMessage: "",
    fileMode: true,
    hideModal: () => {},
    modalShow: true,
    modalStatic: false,
    multiple: false,
    onOk: () => {},
    optionsShow: false,
    undoShow: false,
});
</script>

<template>
    <BModal v-if="modalShow" modal-class="selection-dialog-modal" visible :static="modalStatic" @hide="hideModal">
        <template v-slot:modal-header>
            <slot name="search" />
        </template>
        <slot name="helper" />
        <BAlert v-if="errorMessage" variant="danger" show>
            {{ errorMessage }}
        </BAlert>
        <div v-else>
            <slot v-if="optionsShow" name="options" />
            <div v-else>
                <FontAwesomeIcon :icon="faSpinner" spin />
                <span>Please wait...</span>
            </div>
        </div>
        <template v-slot:modal-footer>
            <div class="d-flex justify-content-between w-100">
                <div>
                    <BButton v-if="undoShow" id="back-btn" size="sm" @click="backFunc">
                        <FontAwesomeIcon :icon="['fas', 'caret-left']" />
                        Back
                    </BButton>
                    <slot v-if="!errorMessage" name="buttons" />
                </div>
                <div>
                    <BButton id="close-btn" size="sm" variant="secondary" @click="hideModal"> Cancel </BButton>
                    <BButton
                        v-if="multiple || !fileMode"
                        id="ok-btn"
                        size="sm"
                        class="file-dialog-modal-ok"
                        variant="primary"
                        :disabled="disableOk"
                        @click="onOk">
                        {{ fileMode ? "Ok" : "Select this folder" }}
                    </BButton>
                </div>
            </div>
        </template>
    </BModal>
</template>

<style>
.selection-dialog-modal .modal-body {
    max-height: 50vh;
    height: 50vh;
    overflow-y: auto;
}
</style>
