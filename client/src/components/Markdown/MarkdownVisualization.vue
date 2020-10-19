<template>
    <span>
        <MarkdownSelector
            v-if="labelShow"
            :initial-value="argumentType"
            :argument-name="argumentName"
            :labels="labels"
            :label-title="selectedLabelTitle"
            @onOk="onLabel"
            @onCancel="onCancel"
        />
        <DataDialog v-if="dataShow" :history="history" format="id" @onOk="onData" @onCancel="onCancel" />
        <b-modal
            v-if="formShow"
            v-model="formShow"
            modal-class="visualization-dialog-modal"
            title="Configure Visualization"
            ok-title="Continue"
            @ok="onOk"
            @cancel="onCancel"
        >
            <Form :inputs="formInputs" @onChange="onChange" class="form-body" />
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
            dataTag: null,
            formData: {},
            formShow: false,
            labelShow: false,
            dataShow: false,
        };
    },
    computed: {
        formInputs() {
            let settings = null;
            if (this.argumentPayload.settings && this.argumentPayload.settings.length > 0) {
                settings = Object.assign({}, this.argumentPayload.settings);
                if (this.argumentPayload.groups && this.argumentPayload.groups.length > 0) {
                    settings.groups = {
                        type: "repeat",
                        title: "Columns",
                        name: "groups",
                        min: 1,
                        inputs: this.argumentPayload.groups.map((x) => {
                            if (x.type == "data_column") {
                                x.is_workflow = true;
                            }
                            return x;
                        }),
                    };
                }
            }
            return settings;
        },
    },
    created() {
        if (this.useLabels) {
            this.labelShow = true;
        } else {
            this.dataShow = true;
        }
    },
    methods: {
        onChange(formDataNew) {
            this.formData = formDataNew;
        },
        onLabel(response) {
            this.dataTag = `output=${response}`;
            this.labelShow = false;
            if (this.formInputs) {
                this.formShow = true;
            } else {
                this.onOk();
            }
        },
        onData(response) {
            this.dataTag = `history_dataset_id=${response}`;
            this.dataShow = false;
            if (this.formInputs) {
                this.formShow = true;
            } else {
                this.onOk();
            }
        },
        onOk() {
            let paramString = "";
            Object.entries(this.formData).forEach(([k, v]) => {
                if (v != undefined) {
                    paramString += `, ${k}="${v}"`;
                }
            });
            this.$emit("onOk", `visualization(visualization_id=${this.argumentName}, ${this.dataTag}${paramString})`);
        },
        onCancel() {
            this.$emit("onCancel");
        },
    },
};
</script>
<style>
.visualization-dialog-modal .modal-body {
    max-height: 50vh;
    height: 50vh;
    overflow-y: auto;
}
</style>
