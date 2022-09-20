<template>
    <CurrentUser v-slot="{ user }">
        <ToolCard
            v-if="hasData"
            :id="configForm.id"
            :user="user"
            :version="configForm.version"
            :title="configForm.name"
            :description="configForm.description"
            :options="configForm"
            :message-text="messageText"
            :message-variant="messageVariant"
            @onChangeVersion="onChangeVersion"
            @onUpdateFavorites="onUpdateFavorites">
            <template v-slot:body>
                <FormElement
                    id="__label"
                    :value="nodeLabel"
                    title="Label"
                    help="Add a step label."
                    :error="errorLabel"
                    @input="onLabel" />
                <FormElement
                    id="__annotation"
                    :value="nodeAnnotation"
                    title="Step Annotation"
                    :area="true"
                    help="Add an annotation or notes to this step. Annotations are available when a workflow is viewed."
                    @input="onAnnotation" />
                <FormDisplay
                    :id="id"
                    :inputs="inputs"
                    :errors="errors"
                    text-enable="Set in Advance"
                    text-disable="Set at Runtime"
                    :workflow-building-mode="true"
                    @onChange="onChange" />
                <FormSection
                    :id="nodeId"
                    :node-inputs="nodeInputs"
                    :node-outputs="nodeOutputs"
                    :node-active-outputs="nodeActiveOutputs"
                    :datatypes="datatypes"
                    :post-job-actions="postJobActions"
                    @onChange="onChangePostJobActions" />
            </template>
        </ToolCard>
    </CurrentUser>
</template>

<script>
import CurrentUser from "components/providers/CurrentUser";
import FormDisplay from "components/Form/FormDisplay";
import ToolCard from "components/Tool/ToolCard";
import FormSection from "./FormSection";
import FormElement from "components/Form/FormElement";
import { checkLabels } from "components/Workflow/Editor/modules/utilities";
import Utils from "utils/utils";

export default {
    components: {
        CurrentUser,
        FormDisplay,
        ToolCard,
        FormElement,
        FormSection,
    },
    props: {
        nodeId: {
            type: String,
            required: true,
        },
        nodeAnnotation: {
            type: String,
            required: true,
        },
        nodeLabel: {
            type: String,
            required: true,
        },
        nodeInputs: {
            type: Array,
            required: true,
        },
        nodeOutputs: {
            type: Array,
            required: true,
        },
        nodeActiveOutputs: {
            type: Object,
            required: true,
        },
        configForm: {
            type: Object,
            required: true,
        },
        datatypes: {
            type: Array,
            required: true,
        },
        getManager: {
            type: Function,
            required: true,
        },
        postJobActions: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            mainValues: {},
            messageText: "",
            messageVariant: "success",
        };
    },
    computed: {
        workflow() {
            return this.getManager();
        },
        id() {
            return `${this.nodeId}:${this.configForm.id}`;
        },
        hasData() {
            return !!this.configForm;
        },
        errorLabel() {
            return checkLabels(this.nodeId, this.nodeLabel, this.workflow.nodes);
        },
        inputs() {
            const inputs = this.configForm.inputs;
            Utils.deepeach(inputs, (input) => {
                if (input.type) {
                    if (["data", "data_collection"].indexOf(input.type) != -1) {
                        input.titleonly = true;
                        input.info = `Data input '${input.name}' (${Utils.textify(input.extensions)})`;
                        input.value = { __class__: "RuntimeValue" };
                    } else {
                        input.connectable = ["rules"].indexOf(input.type) == -1;
                        input.collapsible_value = {
                            __class__: "RuntimeValue",
                        };
                        input.is_workflow =
                            (input.options && input.options.length === 0) ||
                            ["integer", "float"].indexOf(input.type) != -1;
                    }
                }
            });
            Utils.deepeach(inputs, (input) => {
                if (input.type === "conditional") {
                    input.connectable = false;
                    input.test_param.collapsible_value = undefined;
                }
            });
            return inputs;
        },
        errors() {
            return this.configForm.errors;
        },
    },
    methods: {
        onAnnotation(newAnnotation) {
            this.$emit("onAnnotation", this.nodeId, newAnnotation);
        },
        onLabel(newLabel) {
            this.$emit("onLabel", this.nodeId, newLabel);
        },
        onChange(values) {
            this.mainValues = values;
            this.postChanges();
        },
        onChangePostJobActions(postJobActions) {
            this.$emit("onChangePostJobActions", this.nodeId, postJobActions);
        },
        onChangeVersion(newVersion) {
            this.messageText = `Now you are using '${this.configForm.name}' version ${newVersion}.`;
            this.postChanges(newVersion);
        },
        onUpdateFavorites(user, newFavorites) {
            user.preferences["favorites"] = newFavorites;
        },
        postChanges(newVersion) {
            const payload = Object.assign({}, this.mainValues);
            console.debug("FormTool - Posting changes.", payload);
            const options = this.configForm;
            let toolId = options.id;
            let toolVersion = options.version;
            if (newVersion) {
                toolId = toolId.replace(toolVersion, newVersion);
                toolVersion = newVersion;
                console.debug("FormTool - Tool version changed.", toolId, toolVersion);
            }
            this.$emit("onSetData", this.nodeId, {
                tool_id: toolId,
                tool_version: toolVersion,
                type: "tool",
                inputs: payload,
            });
        },
    },
};
</script>
