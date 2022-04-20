<template>
    <b-modal v-if="modalShow" modal-class="selection-dialog-modal" visible :static="modalStatic" @hide="hideModal">
        <template v-slot:modal-header>
            <slot name="search"> </slot>
        </template>
        <slot name="helper"> </slot>
        <b-alert v-if="errorMessage" variant="danger" show v-html="errorMessage" />
        <div v-else>
            <slot v-if="optionsShow" name="options"> </slot>
            <div v-else><span class="fa fa-spinner fa-spin" /> <span>Please wait...</span></div>
        </div>
        <template v-slot:modal-footer>
            <div class="w-100">
                <div v-if="!errorMessage">
                    <slot name="buttons"> </slot>
                    <b-btn size="sm" class="float-right selection-dialog-modal-cancel" @click="hideModal">
                        Cancel
                    </b-btn>
                </div>
                <div v-else>
                    <b-btn v-if="undoShow" id="back-btn" size="sm" class="float-left" @click="backFunc">
                        <font-awesome-icon :icon="['fas', 'caret-left']" />
                        Back
                    </b-btn>
                    <b-btn id="close-btn" size="sm" class="float-right" variant="primary" @click="hideModal">
                        Close
                    </b-btn>
                </div>
            </div>
        </template>
    </b-modal>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

Vue.use(BootstrapVue);

export default {
    components: {
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
