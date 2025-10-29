<template>
    <div :step-label="model.step_label">
        <FormCard :title="model.fixed_title" :icon="icon" :collapsible="true" :expanded.sync="expanded">
            <template v-slot:title>
                <span v-if="credentialInfo?.toolId" v-b-tooltip.hover title="Uses credentials">
                    <FontAwesomeIcon :icon="faKey" fixed-width />
                </span>
            </template>
            <template v-slot:body>
                <ToolCredentials
                    v-if="credentialInfo?.toolId"
                    :tool-id="credentialInfo.toolId"
                    :tool-version="credentialInfo.toolVersion" />
                <FormMessage :message="errorText" variant="danger" :persistent="true" />
                <FormDisplay
                    :inputs="modelInputs"
                    :sustain-repeats="true"
                    :sustain-conditionals="true"
                    :replace-params="replaceParams"
                    :validation-scroll-to="validationScrollTo"
                    collapsed-enable-text="Edit"
                    collapsed-enable-icon="fa fa-edit"
                    collapsed-disable-text="Undo"
                    collapsed-disable-icon="fa fa-undo"
                    @onChange="onChange"
                    @onValidation="onValidation" />
            </template>
        </FormCard>
    </div>
</template>

<script>
import { faKey } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { mapState } from "pinia";

import { visitInputs } from "@/components/Form/utilities";
import WorkflowIcons from "@/components/Workflow/icons";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";

import { getTool } from "./services";

import FormCard from "@/components/Form/FormCard.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";
import FormMessage from "@/components/Form/FormMessage.vue";
import ToolCredentials from "@/components/Tool/ToolCredentials.vue";

export default {
    components: {
        FontAwesomeIcon,
        ToolCredentials,
        FormDisplay,
        FormCard,
        FormMessage,
    },
    props: {
        model: {
            type: Object,
            required: true,
        },
        replaceParams: {
            type: Object,
            default: null,
        },
        validationScrollTo: {
            type: Array,
            required: true,
        },
        historyId: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            faKey,
            expanded: this.model.expanded,
            errorText: null,
            modelData: {},
            modelIndex: {},
            modelInputs: this.model.inputs,
        };
    },
    computed: {
        ...mapState(useHistoryItemsStore, ["lastUpdateTime"]),
        credentialInfo() {
            if (!this.model.credentials?.length) {
                return null;
            }

            return {
                toolId: this.model.id,
                toolVersion: this.model.version,
                toolCredentials: this.model.credentials,
            };
        },
        icon() {
            return WorkflowIcons[this.model.step_type];
        },
        historyStatusKey() {
            return `${this.historyId}_${this.lastUpdateTime}`;
        },
    },
    watch: {
        validationScrollTo() {
            if (this.validationScrollTo.length > 0) {
                this.expanded = true;
            }
        },
        historyStatusKey() {
            this.onHistoryChange();
        },
    },
    methods: {
        onCreateIndex() {
            this.modelIndex = {};
            visitInputs(this.modelInputs, (input, name) => {
                this.modelIndex[name] = input;
            });
        },
        onHistoryChange() {
            this.onUpdate();
        },
        onChange(data, refreshRequest) {
            this.modelData = data;
            if (refreshRequest) {
                this.onUpdate();
            }
            this.$emit("onChange", this.model.index, data);
        },
        onUpdate() {
            getTool(this.model.id, this.model.version, this.modelData, this.historyId).then(
                (newModel) => {
                    this.onCreateIndex();
                    visitInputs(newModel.inputs, (newInput, name) => {
                        const input = this.modelIndex[name];
                        input.options = newInput.options;
                        input.textable = newInput.textable;
                    });
                    this.modelInputs = JSON.parse(JSON.stringify(this.modelInputs));
                },
                (errorText) => {
                    this.errorText = errorText;
                },
            );
        },
        onValidation(validation) {
            this.$emit("onValidation", this.model.index, validation);
        },
    },
};
</script>
