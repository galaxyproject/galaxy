<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretLeft, faCheck, faSpinner, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BModal } from "bootstrap-vue";
import { ref } from "vue";

import DataDialogSearch from "@/components/SelectionDialog/DataDialogSearch.vue";
import DataDialogTable from "@/components/SelectionDialog/DataDialogTable.vue";

library.add(faCaretLeft, faCheck, faSpinner, faTimes);

export interface Record {
    id: string;
    label: string;
    details: string;
    isLeaf: boolean;
    url: string;
    labelTitle: string | undefined;
}

interface Props {
    disableOk?: boolean;
    errorMessage?: string;
    fileMode?: boolean;
    isBusy?: boolean;
    items: Array<Record>;
    modalShow?: boolean;
    modalStatic?: boolean;
    multiple?: boolean;
    optionsShow?: boolean;
    undoShow?: boolean;
    selectAllIcon?: string;
    showDetails?: boolean;
    showSelectIcon?: boolean;
    showTime?: boolean;
    title?: string;
}

withDefaults(defineProps<Props>(), {
    disableOk: false,
    errorMessage: "",
    fileMode: true,
    isBusy: false,
    modalShow: true,
    modalStatic: false,
    multiple: false,
    optionsShow: false,
    undoShow: false,
    showDetails: false,
    showSelectIcon: false,
    showTime: false,
    title: "",
});

const emit = defineEmits<{
    (e: "onBack"): void;
    (e: "onCancel"): void;
    (e: "onClick", record: Record): void;
    (e: "onOk"): void;
    (e: "onOpen", record: Record): void;
    (e: "onSelectAll"): void;
}>();

const filter = ref("");
</script>

<template>
    <BModal
        v-if="modalShow"
        modal-class="selection-dialog-modal"
        visible
        :static="modalStatic"
        @hide="emit('onCancel')">
        <template v-slot:modal-header>
            <DataDialogSearch v-model="filter" :title="title" />
        </template>
        <slot name="helper" />
        <BAlert v-if="errorMessage" variant="danger" show>
            {{ errorMessage }}
        </BAlert>
        <div v-else>
            <DataDialogTable
                v-if="optionsShow"
                :filter="filter"
                :is-busy="isBusy"
                :items="items"
                :multiple="multiple"
                :select-all-icon="selectAllIcon"
                :show-details="showDetails"
                :show-select-icon="showSelectIcon"
                :show-time="showTime"
                @onClick="emit('onClick', $event)"
                @onOpen="emit('onOpen', $event)"
                @onSelectAll="emit('onSelectAll')" />
            <div v-else>
                <FontAwesomeIcon :icon="faSpinner" spin />
                <span>Please wait...</span>
            </div>
        </div>
        <template v-slot:modal-footer>
            <div class="d-flex justify-content-between w-100">
                <div>
                    <BButton v-if="undoShow" id="back-btn" size="sm" @click="emit('onBack')">
                        <FontAwesomeIcon :icon="['fas', 'caret-left']" />
                        Back
                    </BButton>
                    <slot v-if="!errorMessage" name="buttons" />
                </div>
                <div>
                    <BButton id="close-btn" size="sm" variant="secondary" @click="emit('onCancel')">
                        <FontAwesomeIcon :icon="['fas', 'times']" />
                        Cancel
                    </BButton>
                    <BButton
                        v-if="multiple || !fileMode"
                        id="ok-btn"
                        size="sm"
                        class="file-dialog-modal-ok"
                        variant="primary"
                        :disabled="disableOk"
                        @click="emit('onOk')">
                        <FontAwesomeIcon :icon="['fas', 'check']" />
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
