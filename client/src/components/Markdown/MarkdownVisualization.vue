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
        <DataDialog v-else :history="history" format="id" @onOk="onData" @onCancel="onCancel" />
    </span>
</template>

<script>
import MarkdownSelector from "./MarkdownSelector";
import DataDialog from "components/DataDialog/DataDialog";

export default {
    components: {
        MarkdownSelector,
        DataDialog,
    },
    props: {
        argumentName: {
            type: String,
            required: true,
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
            formShow: false,
        };
    },
    methods: {
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
