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
import { BButton, BButtonGroup, BFormInput } from "bootstrap-vue";
//@ts-ignore deprecated package without types (vue 2, remove this comment on vue 3 migration)
import { BoxSelect, Workflow } from "lucide-vue";
import { storeToRefs } from "pinia";
import { computed, toRefs, watch } from "vue";

import { RemoveAllFreehandCommentsAction } from "@/components/Workflow/Editor/Actions/commentActions";
import { useUid } from "@/composables/utils/uid";
import { useWorkflowStores } from "@/composables/workflowStores";
import { type CommentTool } from "@/stores/workflowEditorToolbarStore";
import { match } from "@/utils/utils";

import { AutoLayoutAction } from "../Actions/stepActions";
import { useSelectionOperations } from "./useSelectionOperations";
import { useToolLogic } from "./useToolLogic";

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
        return "关闭吸附功能 (Ctrl + 2)";
    } else {
        return "激活吸附功能 (Ctrl + 2)";
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
        return "隐藏工具栏";
    } else {
        return "显示工具栏";
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
                <BButtonGroup vertical>
                    <BButton
                        v-b-tooltip.hover.noninteractive.right
                        class="button"
                        data-tool="pointer"
                        title="指针工具 (Ctrl + 1)"
                        :pressed="currentTool === 'pointer'"
                        variant="outline-primary"
                        @click="onClickPointer">
                        <FontAwesomeIcon icon="fa-mouse-pointer" size="lg" />
                    </BButton>
                    <BButton
                        v-b-tooltip.hover.noninteractive.right
                        class="button"
                        data-tool="toggle_snap"
                        :title="snapButtonTitle"
                        :pressed.sync="snapActive"
                        variant="outline-primary">
                        <FontAwesomeIcon icon="fa-magnet" size="lg" />
                    </BButton>
                </BButtonGroup>

                <BButtonGroup vertical>
                    <BButton
                        v-b-tooltip.hover.noninteractive.right
                        class="button font-weight-bold"
                        data-tool="text_comment"
                        title="文本注释 (Ctrl + 3)"
                        :pressed="currentTool === 'textComment'"
                        variant="outline-primary"
                        @click="() => onCommentToolClick('textComment')">
                        <span class="icon-t">T</span>
                    </BButton>
                    <BButton
                        v-b-tooltip.hover.noninteractive.right
                        class="button"
                        data-tool="markdown_comment"
                        title="Markdown注释 (Ctrl + 4)"
                        :pressed="currentTool === 'markdownComment'"
                        variant="outline-primary"
                        @click="() => onCommentToolClick('markdownComment')">
                        <FontAwesomeIcon :icon="['fab', 'markdown']" size="lg" />
                    </BButton>
                    <BButton
                        v-b-tooltip.hover.noninteractive.right
                        class="button"
                        data-tool="frame_comment"
                        title="框架注释 (Ctrl + 5)"
                        :pressed="currentTool === 'frameComment'"
                        variant="outline-primary"
                        @click="() => onCommentToolClick('frameComment')">
                        <FontAwesomeIcon icon="fa-object-group" size="lg" />
                    </BButton>
                </BButtonGroup>

                <BButtonGroup vertical>
                    <BButton
                        v-b-tooltip.hover.noninteractive.right
                        title="自由绘制笔 (Ctrl + 6)"
                        data-tool="freehand_pen"
                        :pressed="currentTool === 'freehandComment'"
                        class="button"
                        variant="outline-primary"
                        @click="() => onCommentToolClick('freehandComment')">
                        <FontAwesomeIcon icon="fa-pen" size="lg" />
                    </BButton>
                    <BButton
                        v-b-tooltip.hover.noninteractive.right
                        title="自由绘制橡皮擦 (Ctrl + 7)"
                        data-tool="freehand_eraser"
                        :pressed="currentTool === 'freehandEraser'"
                        class="button"
                        variant="outline-primary"
                        @click="() => onCommentToolClick('freehandEraser')">
                        <FontAwesomeIcon icon="fa-eraser" size="lg" />
                    </BButton>
                </BButtonGroup>

                <BButton
                    v-b-tooltip.hover.noninteractive.right
                    title="框选工具 (Ctrl + 8)"
                    data-tool="box_select"
                    :pressed="currentTool === 'boxSelect'"
                    class="button"
                    variant="outline-primary"
                    @click="onClickBoxSelect">
                    <BoxSelect />
                </BButton>

                <BButton
                    id="auto-layout-button"
                    v-b-tooltip.hover.noninteractive.right
                    title="自动布局 (Ctrl + 9)"
                    data-tool="auto_layout"
                    class="button"
                    variant="outline-primary"
                    @click="autoLayout">
                    <Workflow />
                </BButton>
            </template>

            <BButton
                v-b-tooltip.hover.noninteractive.right
                class="toggle-visibility-button"
                :title="toggleVisibilityButtonTitle"
                variant="outline-primary"
                @click="toolbarVisible = !toolbarVisible">
                <FontAwesomeIcon v-if="toolbarVisible" icon="fa-chevron-up" />
                <FontAwesomeIcon v-else icon="fa-chevron-down" />
            </BButton>
        </div>
        <div v-if="toolbarVisible" class="options">
            <div v-if="anySelected" class="selection-options">
                <span>{{ selectedCountText }}</span>

                <BButtonGroup>
                    <BButton class="button" title="清除选择" @click="deselectAll">
                        清除 <FontAwesomeIcon icon="fa-times" />
                    </BButton>
                    <BButton class="button" title="复制所选" @click="duplicateSelection">
                        复制 <FontAwesomeIcon icon="fa-clone" />
                    </BButton>
                    <BButton class="button" title="删除所选" @click="deleteSelection">
                        删除 <FontAwesomeIcon icon="fa-trash" />
                    </BButton>
                </BButtonGroup>
            </div>

            <div
                v-if="
                    toolbarStore.snapActive &&
                    !['freehandComment', 'freehandEraser', 'boxSelect'].includes(toolbarStore.currentTool)
                "
                class="option wide">
                <label :for="snappingDistanceId" class="flex-label">
                    <span class="font-weight-bold">吸附距离</span>
                    {{ toolbarStore.snapDistance }} 像素
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
                <BButtonGroup>
                    <BButton
                        :pressed.sync="commentOptions.bold"
                        variant="outline-primary"
                        class="button font-weight-bold"
                        data-option="toggle-bold">
                        粗体
                    </BButton>
                    <BButton
                        :pressed.sync="commentOptions.italic"
                        variant="outline-primary"
                        class="button font-italic"
                        data-option="toggle-italic">
                        斜体
                    </BButton>
                </BButtonGroup>
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
                    <span class="font-weight-bold">文本大小</span>
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
                    <span class="font-weight-bold">大小</span>
                    {{ commentOptions.lineThickness }} 像素
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
                    <span class="font-weight-bold">平滑度</span>
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
                <BButton
                    class="button"
                    data-option="remove-freehand"
                    title="删除所有自由绘制注释"
                    @click="onRemoveAllFreehand">
                    删除全部
                </BButton>
            </div>

            <div v-if="currentTool === 'boxSelect'" class="option buttons">
                <BButtonGroup>
                    <BButton
                        :pressed="toolbarStore.boxSelectMode === 'add'"
                        class="button"
                        data-option="select-mode-add"
                        variant="outline-primary"
                        title="添加项目到选择"
                        @click="toolbarStore.boxSelectMode = 'add'">
                        添加到选择
                    </BButton>
                    <BButton
                        :pressed="toolbarStore.boxSelectMode === 'remove'"
                        class="button"
                        data-option="select-mode-remove"
                        variant="outline-primary"
                        title="从选择中移除项目"
                        @click="toolbarStore.boxSelectMode = 'remove'">
                        从选择中移除
                    </BButton>
                </BButtonGroup>
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
        align-items: center;
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
        align-items: start;
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
