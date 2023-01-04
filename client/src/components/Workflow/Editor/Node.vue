<template>
    <draggable-wrapper
        :id="idString"
        ref="el"
        :scale="scale"
        :root-offset="rootOffset"
        :name="name"
        :node-label="title"
        :class="classes"
        :style="style"
        @move="onMoveTo"
        @pan-by="onPanBy">
        <div class="node-header unselectable clearfix" @click="makeActive" @keyup.enter="makeActive">
            <b-button
                v-b-tooltip.hover
                class="node-destroy py-0 float-right"
                variant="primary"
                size="sm"
                aria-label="destroy node"
                title="Remove"
                @click.prevent.stop="remove">
                <i class="fa fa-times" />
            </b-button>
            <b-button
                v-if="isEnabled"
                :id="popoverId"
                class="node-recommendations py-0 float-right"
                variant="primary"
                size="sm"
                aria-label="tool recommendations">
                <i class="fa fa-arrow-right" />
            </b-button>
            <b-popover
                v-if="isEnabled"
                :target="popoverId"
                triggers="hover"
                placement="bottom"
                :show.sync="popoverShow">
                <Recommendations
                    v-if="popoverShow"
                    :step-id="id"
                    :datatypes-mapper="datatypesMapper"
                    @onCreate="onCreate" />
            </b-popover>
            <b-button
                v-if="canClone"
                v-b-tooltip.hover
                class="node-clone py-0 float-right"
                variant="primary"
                size="sm"
                aria-label="clone node"
                title="Duplicate"
                @click.prevent.stop="onClone">
                <i class="fa fa-files-o" />
            </b-button>
            <i :class="iconClass" />
            <span
                v-b-tooltip.hover
                title="Index of the step in the workflow run form. Steps are ordered by distance to the upper-left corner of the window; inputs are listed first."
                >{{ step.id + 1 }}:
            </span>
            <span class="node-title">{{ title }}</span>
        </div>
        <b-alert v-if="!!errors" variant="danger" show class="node-error" @click="makeActive">
            {{ errors }}
        </b-alert>
        <div v-else class="node-body" @click="makeActive" @keyup.enter="makeActive">
            <node-input
                v-for="input in inputs"
                :key="input.name"
                :input="input"
                :step-id="id"
                :datatypes-mapper="datatypesMapper"
                :step-position="step.position"
                :root-offset="rootOffset"
                :parent-offset="position"
                v-on="$listeners"
                @onChange="onChange" />
            <div v-if="showRule" class="rule" />
            <node-output
                v-for="output in outputs"
                :key="output.name"
                :output="output"
                :workflow-outputs="workflowOutputs"
                :post-job-actions="postJobActions"
                :step-id="id"
                :step-type="step.type"
                :step-position="step.position"
                :root-offset="rootOffset"
                :parent-offset="position"
                :datatypes-mapper="datatypesMapper"
                v-on="$listeners"
                @stopDragging="onStopDragging"
                @onToggle="onToggleOutput"
                @onChange="onChange" />
        </div>
    </draggable-wrapper>
</template>

<script lang="ts" setup>
import type { PropType, Ref } from "vue";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import WorkflowIcons from "@/components/Workflow/icons";
// TODO: implement scheme for loading tool state here
// import LoadingSpan from "@/components/LoadingSpan.vue";
import { getGalaxyInstance } from "@/app";
import Recommendations from "@/components/Workflow/Editor/Recommendations.vue";
import NodeInput from "@/components/Workflow/Editor/NodeInput.vue";
import NodeOutput from "@/components/Workflow/Editor/NodeOutput.vue";
import DraggableWrapper from "@/components/Workflow/Editor/DraggablePan.vue";
import { ActiveOutputs } from "./modules/outputs";
import { computed, ref } from "vue";
import { useNodePosition } from "@/components/Workflow/Editor/composables/useNodePosition";
import { useWorkflowStateStore, type XYPosition } from "@/stores/workflowEditorStateStore";
import type { Step } from "@/stores/workflowStepStore";
import { DatatypesMapperModel } from "@/components/Datatypes/model";
import type { UseElementBoundingReturn } from "@vueuse/core";

Vue.use(BootstrapVue);

const props = defineProps({
    id: { type: Number, required: true },
    contentId: { type: String as PropType<string | null>, default: null },
    name: { type: String as PropType<string | null>, default: null },
    step: { type: Object as PropType<Step>, required: true },
    datatypesMapper: { type: DatatypesMapperModel, required: true },
    activeNodeId: {
        type: null as unknown as PropType<number | null>,
        required: true,
        validator: (v: any) => typeof v === "number" || v === null,
    },
    rootOffset: { type: Object as PropType<UseElementBoundingReturn>, required: true },
    scale: { type: Number, default: 1 },
    highlight: { type: Boolean, default: false },
});

const emit = defineEmits([
    "onRemove",
    "onActivate",
    "onChange",
    "onCreate",
    "onUpdate",
    "onClone",
    "onUpdateStepPosition",
    "pan-by",
    "stopDragging",
]);

const popoverShow = ref(false);
const popoverId = computed(() => `popover-${props.id}`);
const scrolledTo = ref(false);

function remove() {
    emit("onRemove", props.id);
}

const el: Ref<HTMLElement | null> = ref(null);
const postJobActions = computed(() => props.step.post_job_actions || {});
const workflowOutputs = computed(() => props.step.workflow_outputs || []);
const stateStore = useWorkflowStateStore();
const position = useNodePosition(el, props.id, stateStore);
const title = computed(() => props.step.label || props.step.name);
const idString = computed(() => `wf-node-step-${props.id}`);
const showRule = computed(() => props.step.inputs.length > 0 && props.step.outputs.length > 0);
const iconClass = computed(() => `icon fa fa-fw ${WorkflowIcons[props.step.type]}`);
const canClone = computed(() => props.step.type !== "subworkflow"); // Why ?
const isEnabled = getGalaxyInstance().config.enable_tool_recommendations; // getGalaxyInstance is not reactive

const isActive = computed(() => props.id === props.activeNodeId);
const classes = computed(() => {
    return {
        "workflow-node": true,
        "node-on-scroll-to": scrolledTo.value,
        "node-highlight": props.highlight || isActive.value,
        "is-active": isActive.value,
    };
});
const style = computed(() => {
    return { top: props.step.position!.top + "px", left: props.step.position!.left + "px" };
});
const activeOutputs = new ActiveOutputs();
const errors = computed(() => props.step.errors);
const inputs = computed(() => props.step.inputs);
const outputs = computed(() => props.step.outputs);

function onMoveTo(position: XYPosition) {
    emit("onUpdateStepPosition", props.id, {
        top: position.y,
        left: position.x,
    });
}

function onPanBy(panBy: XYPosition) {
    emit("pan-by", panBy);
}

function onStopDragging() {
    emit("stopDragging");
}

function onChange() {
    emit("onChange");
}

function onCreate(contentId: string, name: string) {
    emit("onCreate", contentId, name);
    popoverShow.value = false;
}

function onClone() {
    emit("onClone", props.id);
}

function onToggleOutput(name: string) {
    activeOutputs.toggle(name);
}

function makeActive() {
    emit("onActivate", props.id);
}
</script>
