<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faMarkdown } from "@fortawesome/free-brands-svg-icons";
import {
    faChevronDown,
    faChevronUp,
    faClone,
    faEraser,
    faMagnet,
    faMousePointer,
    faObjectGroup,
    faPen,
    faTimes,
    faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useMagicKeys, whenever } from "@vueuse/core";
import { BFormInput } from "bootstrap-vue";
//@ts-ignore deprecated package without types (vue 2, remove this comment on vue 3 migration)
import { BoxSelect, Workflow } from "lucide-vue";
import { storeToRefs } from "pinia";
import { computed, toRefs, watch } from "vue";

import { RemoveAllFreehandCommentsAction } from "@/components/Workflow/Editor/Actions/commentActions";
import { useUid } from "@/composables/utils/uid";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { CommentTool } from "@/stores/workflowEditorToolbarStore";
import { match } from "@/utils/utils";

import { AutoLayoutAction } from "../Actions/stepActions";
import { useSelectionOperations } from "./useSelectionOperations";
import { useToolLogic } from "./useToolLogic";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";
import ColorSelector from "@/components/Workflow/Editor/Comments/ColorSelector.vue";

library.add(
    faMarkdown,
    faChevronDown,
    faChevronUp,
    faClone,
    faEraser,
    faMagnet,
    faMousePointer,
    faObjectGroup,
    faPen,
    faTimes,
    faTrash
);

const { toolbarStore, undoRedoStore, commentStore, workflowId } = useWorkflowStores();
const { snapActive, currentTool } = toRefs(toolbarStore);

const { commentOptions } = toolbarStore;
const { toolbarVisible } = storeToRefs(toolbarStore);

const snapButtonTitle = computed(() => {
    if (snapActive.value) {
        return "Deactivate snapping (Ctrl + 2)";
    } else {
        return "Activate snapping (Ctrl + 2)";
    }
});

function onClickPointer() {
    currentTool.value = "pointer";
}

function onClickBoxSelect() {
    toolbarStore.boxSelectMode = "add";
    currentTool.value = "boxSelect";
}

function onCommentToolClick(comment: CommentTool) {
    currentTool.value = comment;
}

watch(
    () => toolbarStore.currentTool,
    (currentTool) => {
        if (currentTool === "pointer") {
            toolbarStore.inputCatcherActive = false;
        } else {
            toolbarStore.inputCatcherActive = true;
        }
    }
);

const snappingDistanceId = useUid("snapping-distance-");

const snappingDistanceRangeValue = computed({
    get() {
        return match(toolbarStore.snapDistance, {
            10: () => "1",
            20: () => "2",
            50: () => "3",
            100: () => "4",
            200: () => "5",
        });
    },
    set(value) {
        toolbarStore.snapDistance = match(parseInt(value), {
            1: () => 10,
            2: () => 20,
            3: () => 50,
            4: () => 100,
            5: () => 200,
        });
    },
});

const fontSizeId = useUid("font-size-");

const fontSize = computed({
    get() {
        return `${commentOptions.textSize}`;
    },
    set(value) {
        commentOptions.textSize = parseInt(value);
    },
});

const thicknessId = useUid("thickness-");

const smoothingId = useUid("smoothing-");

function onRemoveAllFreehand() {
    undoRedoStore.applyAction(new RemoveAllFreehandCommentsAction(commentStore));
}

useToolLogic();

const { ctrl_1, ctrl_2, ctrl_3, ctrl_4, ctrl_5, ctrl_6, ctrl_7, ctrl_8, ctrl_9 } = useMagicKeys();

whenever(ctrl_1!, () => (toolbarStore.currentTool = "pointer"));
whenever(ctrl_2!, () => (toolbarStore.snapActive = !toolbarStore.snapActive));
whenever(ctrl_3!, () => (toolbarStore.currentTool = "textComment"));
whenever(ctrl_4!, () => (toolbarStore.currentTool = "markdownComment"));
whenever(ctrl_5!, () => (toolbarStore.currentTool = "frameComment"));
whenever(ctrl_6!, () => (toolbarStore.currentTool = "freehandComment"));
whenever(ctrl_7!, () => (toolbarStore.currentTool = "freehandEraser"));
whenever(ctrl_8!, () => (toolbarStore.currentTool = "boxSelect"));
whenever(ctrl_9!, () => autoLayout());

const toggleVisibilityButtonTitle = computed(() => {
    if (toolbarVisible.value) {
        return "hide Toolbar";
    } else {
        return "show Toolbar";
    }
});

const { anySelected, selectedCountText, deleteSelection, deselectAll, duplicateSelection } = useSelectionOperations();

function autoLayout() {
    undoRedoStore.applyAction(new AutoLayoutAction(workflowId));
}
</script>

<template>
    <div class="workflow-editor-toolbar">
        <div class="tools">
            <template v-if="toolbarVisible">
                <GButtonGroup vertical>
                    <GButton
                        tooltip
                        tooltip-placement="right"
                        outline
                        color="blue"
                        class="button"
                        data-tool="pointer"
                        title="Pointer Tool (Ctrl + 1)"
                        :pressed="currentTool === 'pointer'"
                        @click="onClickPointer">
                        <FontAwesomeIcon icon="fa-mouse-pointer" size="lg" />
                    </GButton>
                    <GButton
                        tooltip
                        tooltip-placement="right"
                        outline
                        color="blue"
                        class="button"
                        data-tool="toggle_snap"
                        :title="snapButtonTitle"
                        :pressed.sync="snapActive">
                        <FontAwesomeIcon icon="fa-magnet" size="lg" />
                    </GButton>
                </GButtonGroup>

                <GButtonGroup vertical>
                    <GButton
                        tooltip
                        tooltip-placement="right"
                        outline
                        color="blue"
                        class="button font-weight-bold"
                        data-tool="text_comment"
                        title="Text comment (Ctrl + 3)"
                        :pressed="currentTool === 'textComment'"
                        @click="() => onCommentToolClick('textComment')">
                        <span class="icon-t">T</span>
                    </GButton>
                    <GButton
                        tooltip
                        tooltip-placement="right"
                        outline
                        color="blue"
                        class="button"
                        data-tool="markdown_comment"
                        title="Markdown comment (Ctrl + 4)"
                        :pressed="currentTool === 'markdownComment'"
                        @click="() => onCommentToolClick('markdownComment')">
                        <FontAwesomeIcon :icon="['fab', 'markdown']" size="lg" />
                    </GButton>
                    <GButton
                        tooltip
                        tooltip-placement="right"
                        outline
                        color="blue"
                        class="button"
                        data-tool="frame_comment"
                        title="Frame comment (Ctrl + 5)"
                        :pressed="currentTool === 'frameComment'"
                        @click="() => onCommentToolClick('frameComment')">
                        <FontAwesomeIcon icon="fa-object-group" size="lg" />
                    </GButton>
                </GButtonGroup>

                <GButtonGroup vertical>
                    <GButton
                        tooltip
                        tooltip-placement="right"
                        outline
                        color="blue"
                        title="Freehand Pen (Ctrl + 6)"
                        data-tool="freehand_pen"
                        :pressed="currentTool === 'freehandComment'"
                        class="button"
                        @click="() => onCommentToolClick('freehandComment')">
                        <FontAwesomeIcon icon="fa-pen" size="lg" />
                    </GButton>
                    <GButton
                        tooltip
                        tooltip-placement="right"
                        outline
                        color="blue"
                        title="Freehand Eraser (Ctrl + 7)"
                        data-tool="freehand_eraser"
                        :pressed="currentTool === 'freehandEraser'"
                        class="button"
                        @click="() => onCommentToolClick('freehandEraser')">
                        <FontAwesomeIcon icon="fa-eraser" size="lg" />
                    </GButton>
                </GButtonGroup>

                <GButton
                    tooltip
                    tooltip-placement="right"
                    outline
                    color="blue"
                    title="Box Select (Ctrl + 8)"
                    data-tool="box_select"
                    :pressed="currentTool === 'boxSelect'"
                    class="button"
                    @click="onClickBoxSelect">
                    <BoxSelect />
                </GButton>

                <GButton
                    id="auto-layout-button"
                    tooltip
                    tooltip-placement="right"
                    outline
                    color="blue"
                    title="Auto Layout (Ctrl + 9)"
                    data-tool="auto_layout"
                    class="button"
                    variant="outline-primary"
                    @click="autoLayout">
                    <Workflow />
                </GButton>
            </template>

            <GButton
                tooltip
                tooltip-placement="right"
                outline
                color="blue"
                class="toggle-visibility-button"
                :title="toggleVisibilityButtonTitle"
                @click="toolbarVisible = !toolbarVisible">
                <FontAwesomeIcon v-if="toolbarVisible" icon="fa-chevron-up" />
                <FontAwesomeIcon v-else icon="fa-chevron-down" />
            </GButton>
        </div>
        <div v-if="toolbarVisible" class="options">
            <div v-if="anySelected" class="selection-options">
                <span>{{ selectedCountText }}</span>

                <GButtonGroup>
                    <GButton class="button" title="clear selection" @click="deselectAll">
                        Clear <FontAwesomeIcon icon="fa-times" />
                    </GButton>
                    <GButton class="button" title="duplicate selected" @click="duplicateSelection">
                        Duplicate <FontAwesomeIcon icon="fa-clone" />
                    </GButton>
                    <GButton class="button" title="delete selected" @click="deleteSelection">
                        Delete <FontAwesomeIcon icon="fa-trash" />
                    </GButton>
                </GButtonGroup>
            </div>

            <div
                v-if="
                    toolbarStore.snapActive &&
                    !['freehandComment', 'freehandEraser', 'boxSelect'].includes(toolbarStore.currentTool)
                "
                class="option wide">
                <label :for="snappingDistanceId" class="flex-label">
                    <span class="font-weight-bold">Snapping Distance</span>
                    {{ toolbarStore.snapDistance }} pixels
                </label>
                <BFormInput
                    :id="snappingDistanceId"
                    v-model="snappingDistanceRangeValue"
                    data-option="snapping-distance"
                    type="range"
                    min="1"
                    max="5"
                    step="1" />
            </div>

            <div v-if="toolbarStore.currentTool === 'textComment'" class="option buttons">
                <GButtonGroup>
                    <GButton
                        :pressed.sync="commentOptions.bold"
                        outline
                        color="blue"
                        class="button font-weight-bold"
                        data-option="toggle-bold">
                        Bold
                    </GButton>
                    <GButton
                        :pressed.sync="commentOptions.italic"
                        outline
                        color="blue"
                        class="button font-italic"
                        data-option="toggle-italic">
                        Italic
                    </GButton>
                </GButtonGroup>
            </div>

            <div
                v-if="!['pointer', 'freehandEraser', 'boxSelect'].includes(toolbarStore.currentTool)"
                class="option buttons">
                <ColorSelector
                    :color="commentOptions.color"
                    class="color-selector"
                    @set-color="(color) => (commentOptions.color = color)" />
            </div>

            <div v-if="toolbarStore.currentTool === 'textComment'" class="option small">
                <label :for="fontSizeId" class="flex-label">
                    <span class="font-weight-bold">Text Size</span>
                    {{ commentOptions.textSize }}00%
                </label>
                <BFormInput
                    :id="fontSizeId"
                    v-model="fontSize"
                    data-option="font-size"
                    type="range"
                    min="1"
                    max="5"
                    step="1" />
            </div>

            <div v-if="toolbarStore.currentTool === 'freehandComment'" class="option small">
                <label :for="thicknessId" class="flex-label">
                    <span class="font-weight-bold">Size</span>
                    {{ commentOptions.lineThickness }} pixels
                </label>
                <BFormInput
                    :id="thicknessId"
                    v-model="commentOptions.lineThickness"
                    data-option="line-thickness"
                    type="range"
                    min="4"
                    max="20"
                    step="1" />
            </div>

            <div v-if="toolbarStore.currentTool === 'freehandComment'" class="option small">
                <label :for="smoothingId" class="flex-label">
                    <span class="font-weight-bold">Smoothing</span>
                    {{ commentOptions.smoothing }}
                </label>
                <BFormInput
                    :id="smoothingId"
                    v-model="commentOptions.smoothing"
                    data-option="smoothing"
                    type="range"
                    min="1"
                    max="10"
                    step="1" />
            </div>

            <div v-if="['freehandComment', 'freehandEraser'].includes(toolbarStore.currentTool)" class="option buttons">
                <GButton
                    class="button"
                    data-option="remove-freehand"
                    title="Remove all freehand comments"
                    @click="onRemoveAllFreehand">
                    Remove all
                </GButton>
            </div>

            <div v-if="currentTool === 'boxSelect'" class="option buttons">
                <GButtonGroup>
                    <GButton
                        :pressed="toolbarStore.boxSelectMode === 'add'"
                        class="button"
                        outline
                        color="blue"
                        data-option="select-mode-add"
                        title="add items to selection"
                        @click="toolbarStore.boxSelectMode = 'add'">
                        Add to selection
                    </GButton>
                    <GButton
                        :pressed="toolbarStore.boxSelectMode === 'remove'"
                        class="button"
                        outline
                        color="blue"
                        data-option="select-mode-remove"
                        title="remove items from selection"
                        @click="toolbarStore.boxSelectMode = 'remove'">
                        Remove from selection
                    </GButton>
                </GButtonGroup>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.workflow-editor-toolbar {
    position: absolute;
    top: 0;
    left: 0;
    z-index: 2000;
    pointer-events: none;
    display: flex;
    width: 100%;

    .tools {
        display: flex;
        flex-direction: column;
        padding: 0.25rem;
        gap: 0.25rem;
        pointer-events: auto;

        .button {
            padding: 0;
            display: grid;
            place-items: center;
            height: 2.25rem;
            width: 2.25rem;
        }

        &:deep(.btn-outline-primary) {
            &:not(.active) {
                background-color: $workflow-editor-bg;

                &:hover {
                    background-color: $brand-primary;
                }
            }
        }
    }

    .toggle-visibility-button {
        height: 1.5rem;
        display: grid;
        place-items: center;
        padding: 0;
        width: 2.25rem;
    }

    .options {
        display: flex;
        height: 3rem;
        padding: 0.25rem;
        gap: 1rem;
        pointer-events: auto;

        .option {
            display: flex;
            flex-direction: column;
            position: relative;

            &.small {
                width: 6rem;
            }

            &.wide {
                width: 12rem;
            }

            label {
                margin-bottom: 0;
            }

            &:not(:last-child)::after {
                content: "";
                position: absolute;
                top: 0.5rem;
                bottom: 0.5rem;
                width: 0;
                right: calc(-0.5rem - 1px);
                align-self: stretch;
                border: 1px solid $border-color;
            }

            &.buttons {
                flex-direction: row;
                align-items: center;
            }

            .button {
                height: 2rem;
                padding: 0 0.5rem;
            }

            &:deep(.btn-outline-primary) {
                &:not(.active) {
                    background-color: $workflow-editor-bg;
                }

                &:hover {
                    background-color: $brand-primary;
                }
            }
        }
    }

    .selection-options {
        flex: 1;
        pointer-events: none;
        display: flex;
        padding: 0.25rem;
        gap: 0.25rem;
        align-items: flex-start;
        flex-direction: column-reverse;
        align-self: flex-start;

        > * {
            pointer-events: auto;
        }

        .button {
            height: 2rem;
            padding: 0 0.5rem;
        }
    }
}

.flex-label {
    display: flex;
    justify-content: space-between;
}

.color-selector {
    position: relative;
}

.icon-t {
    font-size: 1.2rem;
}
</style>
