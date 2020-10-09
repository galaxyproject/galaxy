<template>
    <span>
        <MarkdownSelector
            v-if="useLabels"
            :initial-value="argumentType"
            :argument-name="argumentName"
            :labels="labels"
            :label-title="selectedLabelTitle"
            @onOk="onOk"
            @onCancel="onCancel"
        />
        <DataDialog v-if="useLabels" :history="history" format="id" @onOk="onData" @onCancel="onCancel" />
        <b-modal v-model="formShow" title="Enter Parameters" ok-title="Continue" @ok="onOk" @cancel="onCancel">
            <Form :inputs="formInputs" @onChange="onChange" />
        </b-modal>
    </span>
</template>

<script>
import MarkdownSelector from "./MarkdownSelector";
import DataDialog from "components/DataDialog/DataDialog";
import Form from "components/Form/Form";

export default {
    components: {
        MarkdownSelector,
        DataDialog,
        Form,
    },
    props: {
        argumentName: {
            type: String,
            required: true,
        },
        argumentPayload: {
            type: Object,
            default: null,
        },
        history: {
            type: String,
            required: true,
        },
        labels: {
            type: Array,
            default: null,
        },
        useLabels: {
            type: Boolean,
            required: true,
        },
    },
    data() {
        return {
            formShow: true,
            formData: {},
        };
    },
    computed: {
        formInputs() {
            return this.argumentPayload.settings;
        },
    },
    methods: {
        onChange(formDataNew) {
            this.formData = formDataNew;
        },
        onOk(response) {
            this.$emit("onOk", `${this.argumentName}(output="${response}")`);
        },
        onData(response) {
            this.$emit("onOk", `${this.argumentName}(history_dataset_id=${response})`);
        },
        onCancel() {
            this.$emit("onCancel");
        },
    },
};
</script>
