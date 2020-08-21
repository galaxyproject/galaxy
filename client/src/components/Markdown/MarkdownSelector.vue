<template>
    <span>
        <b-modal v-model="modalShow" :title="title" ok-title="Continue" @ok="onOk" @cancel="onCancel">
            <div class="ml-2">
                <b-form-radio v-model="selectedValue" name="labels" :value="initialValue">
                    <b>{{ selectTitle }}</b>
                </b-form-radio>
                <h5 class="mt-3">{{ labelTitle }}:</h5>
                <div v-if="hasLabels">
                    <b-form-radio
                        v-for="(label, index) in labels"
                        v-model="selectedValue"
                        class="my-2"
                        name="labels"
                        :key="index"
                        :value="index"
                    >
                        {{ label }}
                    </b-form-radio>
                </div>
                <b-alert v-else show variant="info">
                    No Labels found. Please specify Labels in the Workflow Editor.
                </b-alert>
            </div>
        </b-modal>
    </span>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: {
        title: {
            type: String,
            default: "Select",
        },
        selectTitle: {
            type: String,
            default: "Search Entries",
        },
        labelTitle: {
            type: String,
            default: "Select by Label",
        },
        labels: {
            type: Array,
            default: null,
        },
        initialValue: {
            type: String,
            default: null,
        },
        argumentName: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            selectedValue: this.initialValue,
            modalShow: true,
        };
    },
    computed: {
        hasLabels() {
            return this.labels && this.labels.length > 0;
        },
    },
    methods: {
        onOk() {
            this.modalShow = false;
            this.$emit("onOk", this.initialValue, this.labels[this.selectedValue]);
        },
        onCancel() {
            this.$emit("onCancel");
        },
    },
};
</script>
