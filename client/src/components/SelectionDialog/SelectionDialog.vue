<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretLeft } from "@fortawesome/free-solid-svg-icons";

Vue.use(BootstrapVue);

library.add(faCaretLeft);

interface Props {
    multiple?: boolean;
    modalStatic?: boolean;
    optionsShow?: boolean;
    errorMessage?: string;
    modalShow?: boolean;
    undoShow?: boolean;
    disableOk?: boolean;
    fileMode?: boolean;
    hideModal?: () => void;
    backFunc?: () => void;
    onOk?: () => void;
}

const props = withDefaults(defineProps<Props>(), {
    multiple: false,
    modalStatic: false,
    errorMessage: "",
    optionsShow: false,
    modalShow: true,
    hideModal: () => {},
    backFunc: () => {},
    onOk: () => {},
    undoShow: false,
    disableOk: false,
    fileMode: true,

});
</script>

<template>
    <b-modal v-if="modalShow" modal-class="selection-dialog-modal" visible :static="modalStatic" @hide="hideModal">
        <template v-slot:modal-header>
            <slot name="search"> </slot>
        </template>
        <slot name="helper"> </slot>
        <b-alert v-if="errorMessage" variant="danger" show>
            {{ errorMessage }}
        </b-alert>
        <div v-else>
            <slot v-if="optionsShow" name="options"> </slot>
            <div v-else><span class="fa fa-spinner fa-spin" /> <span>Please wait...</span></div>
        </div>
        <template v-slot:modal-footer>
            <div class="d-flex justify-content-between w-100">
                <div>
                    <b-btn v-if="undoShow" id="back-btn" size="sm" @click="backFunc">
                        <FontAwesomeIcon :icon="['fas', 'caret-left']" />
                        Back
                    </b-btn>
                    <slot v-if="!errorMessage" name="buttons"/>
                </div>
                <div>
                    <b-btn id="close-btn" size="sm" variant="secondary" @click="hideModal">
                        Cancel
                    </b-btn>
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
    </b-modal>
</template>

<style>
.selection-dialog-modal .modal-body {
    max-height: 50vh;
    height: 50vh;
    overflow-y: auto;
}
</style>
