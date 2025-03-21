<template>
    <ToolCard
        v-if="hasData"
        :id="configForm.id"
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
                :value="label"
                title="标签"
                help="添加步骤标签。"
                :error="uniqueErrorLabel"
                @input="onLabel" />
            <FormElement
                id="__annotation"
                :value="annotation"
                title="步骤注释"
                :area="true"
                help="为此步骤添加注释或备注。查看工作流时可以看到这些注释。"
                @input="onAnnotation" />
            <FormConditional :step="step" @onUpdateStep="(id, step) => $emit('onUpdateStep', id, step)" />
            <div class="mt-2 mb-4">
                <Heading h2 separator bold size="sm"> 工具参数 </Heading>
                <FormDisplay
                    :id="id"
                    :key="formKey"
                    :inputs="inputs"
                    :errors="errors"
                    text-enable="提前设置"
                    text-disable="运行时设置"
                    :workflow-building-mode="true"
                    @onChange="onChange" />
            </div>
            <div class="mt-2 mb-4">
                <Heading h2 separator bold size="sm"> 附加选项 </Heading>
                <FormSection
                    :id="stepId"
                    :key="formKey"
                    :node-inputs="stepInputs"
                    :node-outputs="stepOutputs"
                    :step="step"
                    :datatypes="datatypes"
                    :post-job-actions="postJobActions"
                    @onChange="onChangePostJobActions" />
            </div>
        </template>
    </ToolCard>
</template>

<script>
import { storeToRefs } from "pinia";
import Utils from "utils/utils";
import { ref, toRef, watch } from "vue";

import { useWorkflowStores } from "@/composables/workflowStores";
import { useRefreshFromStore } from "@/stores/refreshFromStore";

import { useStepProps } from "../composables/useStepProps";
import { useUniqueLabelError } from "../composables/useUniqueLabelError";

import FormConditional from "./FormConditional.vue";
import FormSection from "./FormSection.vue";
import Heading from "@/components/Common/Heading.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";
import FormElement from "@/components/Form/FormElement.vue";
import ToolCard from "@/components/Tool/ToolCard.vue";

export default {
    components: {
        FormDisplay,
        ToolCard,
        FormElement,
        FormConditional,
        FormSection,
        Heading,
    },
    props: {
        step: {
            // type Step from @/stores/workflowStepStore
            type: Object,
            required: true,
        },
        datatypes: {
            type: Array,
            required: true,
        },
    },
    emits: ["onSetData", "onUpdateStep", "onChangePostJobActions", "onAnnotation", "onLabel"],
    setup(props, { emit }) {
        const { stepId, annotation, label, stepInputs, stepOutputs, configForm, postJobActions } = useStepProps(
            toRef(props, "step")
        );
        const { stepStore } = useWorkflowStores();
        const uniqueErrorLabel = useUniqueLabelError(stepStore, label);

        const { formKey } = storeToRefs(useRefreshFromStore());
        const mainValues = ref(null);

        watch(
            () => formKey.value,
            () => (mainValues.value = null)
        );

        return {
            stepId,
            annotation,
            label,
            stepInputs,
            stepOutputs,
            configForm,
            postJobActions,
            uniqueErrorLabel,
            formKey,
            mainValues,
        };
    },
    data() {
        return {
            messageText: "",
            messageVariant: "success",
        };
    },
    computed: {
        id() {
            // Make sure we compute a unique id. Local tools don't include the version in the id,
            // but updating tool form when switching tool versions requires that the id changes.
            // (see https://github.com/galaxyproject/galaxy/blob/f5e07b11f0996e75b2b6f27896b2301d8fa8717d/client/src/components/Form/FormDisplay.vue#L108)
            return `${this.stepId}:${this.configForm.id}/${this.configForm.version}`;
        },
        toolCardId() {
            return `${this.stepId}`;
        },
        hasData() {
            return !!this.configForm?.id;
        },
        inputs() {
            // TODO: Refactor
            // This code contains a computed side-effect and prop mutation.
            // Both should be refactored
            const inputs = this.configForm.inputs;
            Utils.deepEach(inputs, (input) => {
                if (input.type) {
                    if (["data", "data_collection"].indexOf(input.type) != -1) {
                        const extensions = Array.isArray(input.extensions) ? Utils.textify(input.extensions) : "";
                        input.titleonly = true;
                        input.info = `Data input '${input.name}' (${extensions})`;
                        input.value = { __class__: "RuntimeValue" };
                    } else {
                        const isRules = input.type === "rules";
                        input.connectable = !isRules;
                        input.collapsible_value = isRules
                            ? undefined
                            : {
                                  __class__: "RuntimeValue",
                              };

                        input.is_workflow =
                            (input.options && input.options.length === 0) ||
                            ["integer", "float"].indexOf(input.type) != -1;
                    }
                }
            });
            Utils.deepEach(inputs, (input) => {
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
            this.$emit("onAnnotation", this.stepId, newAnnotation);
        },
        onLabel(newLabel) {
            this.$emit("onLabel", this.stepId, newLabel);
        },
        /**
         * Change event is triggered on component creation and input changes.
         * @param { Object } values contains flat key-value pairs `prefixed-name=value`
         */
        onChange(values) {
            const initialRequest = this.mainValues === null;
            this.mainValues = values;
            if (!initialRequest) {
                this.postChanges();
            }
        },
        onChangePostJobActions(postJobActions) {
            this.$emit("onChangePostJobActions", this.stepId, postJobActions);
        },
        onChangeVersion(newVersion) {
            this.messageText = `现在你在使用 '${this.configForm.name}' 版本 ${newVersion}.`;
            this.postChanges(newVersion);
        },
        onUpdateFavorites(user, newFavorites) {
            user.preferences["favorites"] = newFavorites;
        },
        postChanges(newVersion) {
            const payload = Object.assign({}, this.mainValues);
            const options = this.configForm;
            let toolId = options.id;
            let toolVersion = options.version;
            if (newVersion) {
                toolId = toolId.replace(toolVersion, newVersion);
                toolVersion = newVersion;
            }
            this.$emit("onSetData", this.stepId, {
                tool_id: toolId,
                tool_version: toolVersion,
                type: "tool",
                inputs: payload,
            });
        },
    },
};
</script>
