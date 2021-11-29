<template>
    <b-modal
        modal-class="selection-dialog-modal"
        v-if="modalShow"
        visible
        ok-only
        ok-title="Close"
        :static="modalStatic"
        @hide="hideModal">
        <template v-slot:modal-header>
            <slot name="search"> </slot>
        </template>
        <b-alert v-if="errorMessage" variant="danger" show v-html="errorMessage" />
        <div v-else>
            <slot name="options" v-if="optionsShow"> </slot>
            <div v-else><span class="fa fa-spinner fa-spin" /> <span>Please wait...</span></div>
        </div>
        <template v-if="!errorMessage" v-slot:modal-footer>
            <div class="w-100">
                <slot name="buttons"> </slot>
                <b-btn size="sm" class="float-right selection-dialog-modal-cancel" @click="hideModal"> Cancel </b-btn>
            </div>
        </template>
    </b-modal>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
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
