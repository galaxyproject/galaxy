<template>
    <div :step-label="model.step_label">
        <FormCard :title="model.fixed_title" :icon="icon" :collapsible="true" :expanded.sync="expanded">
            <template v-slot:body>
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
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEdit, faUndo } from "@fortawesome/free-solid-svg-icons";
import { getGalaxyInstance } from "app";
import FormCard from "components/Form/FormCard";
import FormDisplay from "components/Form/FormDisplay";
import FormMessage from "components/Form/FormMessage";
import { visitInputs } from "components/Form/utilities";
import WorkflowIcons from "components/Workflow/icons";
import { mapState } from "pinia";
import { useHistoryItemsStore } from "stores/historyItemsStore";

import { getTool } from "./services";

library.add(faEdit, faUndo);

export default {
    components: {
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
            expanded: this.model.expanded,
            errorText: null,
            modelData: {},
            modelIndex: {},
            modelInputs: this.model.inputs,
        };
    },
    computed: {
        ...mapState(useHistoryItemsStore, ["lastUpdateTime"]),
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
            const Galaxy = getGalaxyInstance();
            if (Galaxy && Galaxy.currHistoryPanel) {
                this.onUpdate();
            }
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
                }
            );
        },
        onValidation(validation) {
            this.$emit("onValidation", this.model.index, validation);
        },
    },
};
</script>
