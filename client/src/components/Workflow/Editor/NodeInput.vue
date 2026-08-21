<script setup lang="ts">
import { faChevronCircleRight, faMinusSquare } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useDebounce, type UseElementBoundingReturn } from "@vueuse/core";
import { storeToRefs } from "pinia";
import {
    computed,
    type ComputedRef,
    inject,
    onBeforeUnmount,
    type PropType,
    type Ref,
    ref,
    toRefs,
    watch,
    watchEffect,
} from "vue";

import { DatatypesMapperModel } from "@/components/Datatypes/model";
import {
    ConnectionAcceptable,
    type InputTerminals,
    type OutputTerminals,
    terminalFactory,
} from "@/components/Workflow/Editor/modules/terminals";
import { presenceGateExpression } from "@/components/Workflow/Editor/modules/whenExpression";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useWorkflowStores } from "@/composables/workflowStores";
import { getConnectionId } from "@/stores/workflowConnectionStore";
import { type InputTerminalSource, presenceGateInputPath } from "@/stores/workflowStepStore";

import { useRelativePosition } from "./composables/relativePosition";
import { useTerminal } from "./composables/useTerminal";

const props = defineProps({
    input: {
        type: Object as PropType<InputTerminalSource>,
        required: true,
    },
    stepId: {
        type: Number,
        required: true,
    },
    datatypesMapper: {
        type: DatatypesMapperModel,
        required: true,
    },
    stepPosition: {
        type: Object,
        required: true,
    },
    rootOffset: {
        type: Object as PropType<UseElementBoundingReturn>,
        required: true,
    },
    scale: {
        type: Number,
        required: true,
    },
    scroll: {
        type: Object,
        required: true,
    },
    parentNode: {
        type: HTMLElement,
        default: null,
    },
    readonly: {
        type: Boolean,
        default: false,
    },
    blank: {
        type: Boolean,
        default: false,
    },
});

onBeforeUnmount(() => {
    stateStore.deleteInputTerminalPosition(props.stepId, props.input.name);
});

const { stepId, input, datatypesMapper } = toRefs(props);

const id = computed(() => `node-${props.stepId}-input-${props.input.name}`);
const { terminal, isMappedOver: isMultiple } = useTerminal(stepId, input, datatypesMapper) as {
    terminal: Ref<InputTerminals>;
    isMappedOver: ComputedRef<boolean>;
};

const dropTarget = ref<HTMLDivElement | null>(null);
const position = useRelativePosition(
    dropTarget,
    computed(() => props.parentNode),
);

const stores = useWorkflowStores();
const { connectionStore, stateStore, stepStore } = stores;
const { confirm } = useConfirmDialog();
const hasTerminals = ref(false);
watchEffect(() => {
    hasTerminals.value = connectionStore.getOutputTerminalsForInputTerminal(id.value).length > 0;
});

const connections = computed(() => {
    return connectionStore.getConnectionsForTerminal(id.value);
});

const invalidConnectionReasons = computed(() =>
    connections.value
        .map((connection) => connectionStore.invalidConnections[getConnectionId(connection)])
        .filter((reason) => reason),
);

const { draggingTerminal } = storeToRefs(stateStore);

interface DropAssessment {
    acceptance: ConnectionAcceptable;
    requiresPresenceGate: boolean;
}

function assessDrop(droppedTerminal: OutputTerminals): DropAssessment {
    const directAcceptance = terminal.value.canAccept(droppedTerminal);
    if (directAcceptance.canAccept) {
        return { acceptance: directAcceptance, requiresPresenceGate: false };
    }
    const gatedAcceptance = terminal.value.canAcceptWithPresenceGate(droppedTerminal);
    if (gatedAcceptance.canAccept) {
        return { acceptance: gatedAcceptance, requiresPresenceGate: true };
    }
    return { acceptance: directAcceptance, requiresPresenceGate: false };
}

const dragAssessment = computed(() => (draggingTerminal.value ? assessDrop(draggingTerminal.value) : null));

const canAccept = computed(() => {
    if (dragAssessment.value) {
        return dragAssessment.value.acceptance;
    } else {
        const firstReason = invalidConnectionReasons.value[0];
        if (firstReason) {
            return new ConnectionAcceptable(false, firstReason);
        }
    }
    return null;
});
const acceptsInput = computed(() => {
    if (canAccept.value?.canAccept) {
        return true;
    } else {
        return false;
    }
});

const endX = computed(
    () => position.value.offsetLeft + props.stepPosition.left + (dropTarget.value?.offsetWidth ?? 2) / 2,
);
const endY = computed(
    () => position.value.offsetTop + props.stepPosition.top + (dropTarget.value?.offsetHeight ?? 2) / 2,
);

watch([endX, endY], ([x, y]) => {
    stateStore.setInputTerminalPosition(props.stepId, props.input.name, { endX: x, endY: y });
});

const isDragging = inject("isDragging");
const label = computed(() => props.input.label || props.input.name);
const reason = computed(() => {
    if (dragAssessment.value?.requiresPresenceGate) {
        return `Drop to connect and run this step only when ${label.value} is provided.`;
    }
    return canAccept.value?.reason ?? undefined;
});
const hasConnections = computed(() => connections.value.length > 0);
const rowClass = computed(() => {
    const classes = ["form-row", "dataRow", "input-data-row"];
    if (!props.blank && props.input?.valid === false) {
        classes.push("form-row-error");
    }
    return classes;
});

const showTooltip = ref(false);

function dragEnter(event: DragEvent) {
    if (reason.value) {
        showTooltip.value = true;
    }
    event.preventDefault();
}

function dragLeave(_event: DragEvent) {
    showTooltip.value = false;
}

function onRemove() {
    const connections = connectionStore.getConnectionsForTerminal(id.value);
    connections.forEach((connection) => terminal.value.disconnect(connection));
}

async function onDrop(event: DragEvent) {
    if (!event.dataTransfer) {
        return;
    }

    const stepOut = JSON.parse(event.dataTransfer.getData("text/plain"));
    const droppedTerminal = terminalFactory(
        stepOut.stepId,
        stepOut.output,
        props.datatypesMapper,
        stores,
    ) as OutputTerminals;

    showTooltip.value = false;

    const assessment = assessDrop(droppedTerminal);
    if (!assessment.acceptance.canAccept) {
        return;
    }
    if (!assessment.requiresPresenceGate) {
        terminal.value.connect(droppedTerminal);
        return;
    }
    await offerPresenceGate(droppedTerminal);
}

/** The dropped value may be absent, and only a gate makes that safe. Offer to write one. */
async function offerPresenceGate(droppedTerminal: OutputTerminals) {
    const confirmed = await confirm(
        `${label.value} may arrive empty, and this step requires it. Run this step only when ${label.value} is provided?`,
        { title: "Run this step conditionally?", okText: "Run only when provided" },
    );
    if (!confirmed) {
        return;
    }
    const step = stepStore.getStep(props.stepId);
    const inputPath = step && presenceGateInputPath(step, props.input.name);
    if (!inputPath) {
        return;
    }

    stores.undoRedoStore
        .action()
        .onRun(() => {
            // Raw, because the surrounding action is what makes this one undo step.
            terminal.value.makeConnection(droppedTerminal);
            terminal.value.setDefaultMapOver(droppedTerminal);
            stepStore.updateStepValue(props.stepId, "when", presenceGateExpression(inputPath));
        })
        .onUndo(() => {
            stepStore.updateStepValue(props.stepId, "when", undefined);
            terminal.value.dropConnection(droppedTerminal);
        })
        .setName("gate step on input")
        .apply();
}

const draggedOver = ref(false);
const draggedOverDebounced = useDebounce(draggedOver, 50);

function nodeDragOver() {
    draggedOver.value = true && Boolean(draggingTerminal.value);
}

function nodeDragOut() {
    draggedOver.value = false;
}

watch(
    () => draggingTerminal.value,
    () => {
        if (!draggingTerminal.value) {
            draggedOver.value = false;
        }
    },
);
</script>

<template>
    <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
    <div class="node-input" :class="rowClass" @drop.prevent="onDrop" @dragover="nodeDragOver" @dragleave="nodeDragOut">
        <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
        <div
            :id="id"
            ref="dropTarget"
            class="input-terminal prevent-zoom"
            :class="{
                'input-active': isDragging,
                'can-accept': acceptsInput,
                'can-not-accept': !acceptsInput,
                'mapped-over': isMultiple,
                'is-dragging': Boolean(draggingTerminal),
                'is-dragover': draggedOverDebounced,
            }"
            :input-name="input.name"
            @dragenter.prevent="dragEnter"
            @dragleave.prevent="dragLeave">
            <b-tooltip v-if="reason" :target="id" :show="showTooltip">
                {{ reason }}
            </b-tooltip>
            <FontAwesomeIcon class="terminal-icon" :icon="faChevronCircleRight" />
        </div>
        <button
            v-if="hasConnections && !readonly"
            v-g-tooltip.hover
            :title="reason"
            class="delete-terminal-button"
            @click="onRemove">
            <FontAwesomeIcon class="delete-button-icon" :icon="faMinusSquare" />
        </button>
        <span v-if="!blank">{{ label }}</span>
        <span
            v-if="!input.optional && !hasTerminals"
            v-g-tooltip.hover
            class="input-required"
            title="Input is required">
            *
        </span>
    </div>
</template>

<style lang="scss">
@import "@/style/scss/theme/blue.scss";
@import "nodeTerminalStyle.scss";

.node-input {
    position: relative;

    .input-required {
        margin-top: $margin-v * 0.25;
        margin-bottom: $margin-v * 0.25;
        color: $brand-danger;
        font-weight: 300;
        cursor: default;
    }
}

.input-terminal {
    @include node-terminal-style(left);

    &.input-active {
        &.can-accept {
            color: $brand-success;
        }

        &.can-not-accept {
            color: $brand-warning;
        }

        // expand size on drag
        &.is-dragging {
            --offset-extra: 10px;
        }

        &.mapped-over.is-dragging {
            --offset-extra: 5px;
        }

        &.is-dragover.can-accept::after {
            outline: solid 3px $brand-primary;
        }
    }
}

.delete-terminal-button {
    position: absolute;
    left: calc(-0.65rem - 5px);
    top: 0.25rem;
    display: grid;
    place-items: center;
    width: 0;
    height: 0;
    padding: 0;
    transition: none;
    border: none;
    background-color: $brand-danger;
    color: $white;

    .delete-button-icon {
        display: none;
        width: 14px;
        height: 14px;
    }

    &:hover,
    &:focus-visible,
    &:focus {
        background-color: $brand-danger;
        color: $white;
    }

    &:focus-visible,
    &:focus {
        box-shadow: 0 0 0 0.2rem $brand-primary;
    }

    .node-input:hover &,
    .node-input:focus-within &,
    .node-input.form-row-error & {
        width: 24px;
        height: 24px;

        .delete-button-icon {
            display: unset;
        }
    }
}
</style>
