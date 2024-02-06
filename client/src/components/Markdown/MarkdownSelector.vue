<template>
    <span>
        <b-modal
            v-model="modalShow"
            :title="title"
            ok-title="Continue"
            @ok="onOk"
            @cancel="onCancel"
            @hidden="onCancel">
            <LabelSelector
                v-model="selectedValue"
                class="ml-2"
                :has-labels="hasLabels"
                :label-title="labelTitle"
                :labels="labels" />
        </b-modal>
    </span>
</template>

<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import LabelSelector from "./LabelSelector";

Vue.use(BootstrapVue);

export default {
    components: { LabelSelector },
    props: {
        labelTitle: {
            type: String,
            default: "",
        },
        labels: {
            type: Array,
            default: null,
        },
        argumentName: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            selectedValue: undefined,
            modalShow: true,
        };
    },
    computed: {
        title() {
            return `Insert '${this.argumentName}'`;
        },
        hasLabels() {
            return this.labels && this.labels.length > 0;
        },
    },
    methods: {
        onOk() {
            this.$emit("onOk", this.selectedValue);
        },
        onCancel() {
            this.$emit("onCancel");
        },
    },
};
</script>
