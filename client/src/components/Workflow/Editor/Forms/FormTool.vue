<template>
    <CurrentUser v-slot="{ user }">
        <ToolCard
            v-if="hasData"
            :id="node.config_form.id"
            :user="user"
            :version="node.config_form.version"
            :title="node.config_form.name"
            :description="node.config_form.description"
            :options="node.config_form"
            :message-text="messageText"
            :message-variant="messageVariant"
            @onChangeVersion="onChangeVersion"
            @onUpdateFavorites="onUpdateFavorites">
            <template v-slot:body>
                <FormElement
                    id="__label"
                    :value="node.label"
                    title="Label"
                    help="Add a step label."
                    :error="errorLabel"
                    @input="onLabel" />
                <FormElement
                    id="__annotation"
                    :value="node.annotation"
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
                    @onChange="onChange" />
                <FormSection :id="nodeId" :get-node="getNode" :datatypes="datatypes" @onChange="onChangeSection" />
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
        datatypes: {
            type: Array,
            required: true,
        },
        getManager: {
            type: Function,
            required: true,
        },
        getNode: {
            type: Function,
            required: true,
        },
    },
    data() {
        return {
            mainValues: {},
            sectionValues: {},
            messageText: "",
            messageVariant: "success",
        };
    },
    computed: {
        node() {
            return this.getNode();
        },
        workflow() {
            return this.getManager();
        },
        id() {
            return `${this.node.id}:${this.node.config_form.id}`;
        },
        nodeId() {
            return this.node.id;
        },
        hasData() {
            return !!this.node.config_form;
        },
        errorLabel() {
            return checkLabels(this.node.id, this.node.label, this.workflow.nodes);
        },
        inputs() {
            const inputs = this.node.config_form.inputs;
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
            return this.node.config_form.errors;
        },
    },
    methods: {
        onAnnotation(newAnnotation) {
            this.$emit("onAnnotation", this.node.id, newAnnotation);
        },
        onLabel(newLabel) {
            this.$emit("onLabel", this.node.id, newLabel);
        },
        onChange(values) {
            this.mainValues = values;
            this.postChanges();
        },
        onChangeSection(values) {
            this.sectionValues = values;
            this.postChanges();
        },
        onChangeVersion(newVersion) {
            this.messageText = `Now you are using '${this.node.config_form.name}' version ${newVersion}.`;
            this.postChanges(newVersion);
        },
        onUpdateFavorites(user, newFavorites) {
            user.preferences["favorites"] = newFavorites;
        },
        postChanges(newVersion) {
            const payload = Object.assign({}, this.mainValues, this.sectionValues);
            console.debug("FormTool - Posting changes.", payload);
            const options = this.node.config_form;
            let toolId = options.id;
            let toolVersion = options.version;
            if (newVersion) {
                toolId = toolId.replace(toolVersion, newVersion);
                toolVersion = newVersion;
                console.debug("FormTool - Tool version changed.", toolId, toolVersion);
            }
            this.$emit("onSetData", this.node.id, {
                tool_id: toolId,
                tool_version: toolVersion,
                type: "tool",
                inputs: payload,
            });
        },
    },
};
</script>
