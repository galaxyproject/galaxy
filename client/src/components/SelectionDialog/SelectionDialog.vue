<template>
    <b-modal v-if="modalShow" modal-class="selection-dialog-modal" visible :static="modalStatic" @hide="hideModal">
        <template v-slot:modal-header>
            <slot name="search"> </slot>
        </template>
        <slot name="helper"> </slot>
        <GAlert v-if="errorMessage" variant="danger" show>
            {{ errorMessage }}
        </GAlert>
        <div v-else>
            <slot v-if="optionsShow" name="options"> </slot>
            <div v-else><span class="fa fa-spinner fa-spin" /> <span>Please wait...</span></div>
        </div>
        <template v-slot:modal-footer>
            <div class="w-100">
                <div v-if="!errorMessage">
                    <slot name="buttons"> </slot>
                    <GButton size="sm" class="float-right selection-dialog-modal-cancel" @click="hideModal">
                        Cancel
                    </GButton>
                </div>
                <div v-else>
                    <GButton v-if="undoShow" id="back-btn" size="sm" class="float-left" @click="backFunc">
                        <FontAwesomeIcon :icon="['fas', 'caret-left']" />
                        Back
                    </GButton>
                    <GButton id="close-btn" size="sm" class="float-right" variant="primary" @click="hideModal">
                        Close
                    </GButton>
                </div>
            </div>
        </template>
    </b-modal>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import { GAlert, GButton } from "@/component-library";

Vue.use(BootstrapVue);

export default {
    components: {
        GAlert,
        GButton,
        FontAwesomeIcon,
    },
    props: {
        multiple: {
            type: Boolean,
            default: false,
        },
        modalStatic: {
            type: Boolean,
            default: false,
        },
        errorMessage: {
            type: String,
            default: null,
        },
        optionsShow: {
            type: Boolean,
            default: false,
        },
        modalShow: {
            type: Boolean,
            default: true,
        },
        hideModal: {
            type: Function,
            required: true,
        },
        backFunc: {
            type: Function,
            required: false,
            default: () => {},
        },
        undoShow: {
            type: Boolean,
            required: false,
        },
    },
};
</script>

<style>
.selection-dialog-modal .modal-body {
    max-height: 50vh;
    height: 50vh;
    overflow-y: auto;
}
</style>
