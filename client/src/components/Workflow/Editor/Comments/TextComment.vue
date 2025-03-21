<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTrashAlt } from "@fortawesome/free-regular-svg-icons";
import { faPalette } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { type UseElementBoundingReturn, useFocusWithin } from "@vueuse/core";
import { BButton, BButtonGroup } from "bootstrap-vue";
import { sanitize } from "dompurify";
import { computed, onMounted, reactive, ref, watch } from "vue";

import { useWorkflowStores } from "@/composables/workflowStores";
import type { TextWorkflowComment, WorkflowCommentColor } from "@/stores/workflowEditorCommentStore";

import { colors } from "./colors";
import { useResizable } from "./useResizable";
import { selectAllText } from "./utilities";

import ColorSelector from "./ColorSelector.vue";
import DraggablePan from "@/components/Workflow/Editor/DraggablePan.vue";

library.add(faTrashAlt, faPalette);

const props = defineProps<{
    comment: TextWorkflowComment;
    rootOffset: UseElementBoundingReturn;
    scale: number;
    readonly?: boolean;
}>();

const emit = defineEmits<{
    (e: "change", data: TextWorkflowComment["data"]): void;
    (e: "resize", size: [number, number]): void;
    (e: "move", position: [number, number]): void;
    (e: "pan-by", position: { x: number; y: number }): void;
    (e: "remove"): void;
    (e: "set-color", color: WorkflowCommentColor): void;
}>();

const resizeContainer = ref<HTMLDivElement>();

useResizable(
    resizeContainer,
    computed(() => props.comment.size),
    ([width, height]) => {
        emit("resize", [width, height]);
        saveText();
    }
);

function escapeAndSanitize(text: string) {
    return sanitize(text, { ALLOWED_TAGS: ["br"] }).replace(/(?:^(\s|&nbsp;)+)|(?:(\s|&nbsp;)+$)/g, "");
}

const editableElement = ref<HTMLSpanElement>();

function getInnerText() {
    const element = editableElement.value;

    if (element) {
        const value = element.innerHTML ?? "";
        return escapeAndSanitize(value);
    } else {
        return "";
    }
}

function saveText() {
    const text = getInnerText();

    if (text !== props.comment.data.text) {
        emit("change", { ...props.comment.data, text });
    }
}

function toggleBold() {
    if (props.comment.data.bold) {
        const { bold: _bold, ...data } = props.comment.data;
        emit("change", data);
    } else {
        emit("change", { ...props.comment.data, bold: true });
    }
}

function toggleItalic() {
    if (props.comment.data.italic) {
        const { italic: _italic, ...data } = props.comment.data;
        emit("change", data);
    } else {
        emit("change", { ...props.comment.data, italic: true });
    }
}

const fontSize = computed(() => props.comment.data.size);
const canIncreaseFontSize = computed(() => fontSize.value < 5);
const canDecreaseFontSize = computed(() => fontSize.value > 1);

function increaseFontSize() {
    if (canIncreaseFontSize.value) {
        emit("change", { ...props.comment.data, size: fontSize.value + 1 });
    }
}

const increaseFontSizeTitle = computed(() =>
    canIncreaseFontSize.value ? `将字体大小增加到 ${fontSize.value + 1}` : "最大字体大小"
);

function decreaseFontSize() {
    if (canDecreaseFontSize.value) {
        emit("change", { ...props.comment.data, size: fontSize.value - 1 });
    }
}

const decreaseFontSizeTitle = computed(() =>
    canDecreaseFontSize.value ? `将字体大小减小到 ${fontSize.value - 1}` : "最小字体大小"
);

function onRootClick() {
    if (!props.readonly) {
        editableElement.value?.focus();
    }
}

function onMove(position: { x: number; y: number }) {
    emit("move", [position.x, position.y]);
}

const showColorSelector = ref(false);
const rootElement = ref<HTMLDivElement>();

const { focused } = useFocusWithin(rootElement);

watch(
    () => focused.value,
    () => {
        if (!focused.value) {
            showColorSelector.value = false;

            if (getInnerText() === "") {
                emit("remove");
            } else {
                saveText();
            }
        }
    }
);

function onSetColor(color: WorkflowCommentColor) {
    emit("set-color", color);
}

const cssVariables = computed(() => {
    const vars: Record<string, string> = {
        "--font-size": `${fontSize.value}rem`,
    };

    if (props.comment.color !== "none") {
        vars["--font-color"] = colors[props.comment.color];
    }

    return vars;
});

const { commentStore } = useWorkflowStores();

function onDoubleClick() {
    if (editableElement.value) {
        selectAllText(editableElement.value);
    }
}

onMounted(() => {
    if (commentStore.isJustCreated(props.comment.id) && editableElement.value) {
        selectAllText(editableElement.value);
    }
});

const position = computed(() => ({ x: props.comment.position[0], y: props.comment.position[1] }));
</script>

<template>
    <div ref="rootElement" class="text-workflow-comment">
        <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions vuejs-accessibility/click-events-have-key-events -->
        <div
            ref="resizeContainer"
            class="resize-container"
            :class="{
                resizable: !props.readonly,
                'prevent-zoom': !props.readonly,
                'multi-selected': commentStore.getCommentMultiSelected(props.comment.id),
            }"
            :style="cssVariables"
            @click="onRootClick">
            <DraggablePan
                v-if="!props.readonly"
                :root-offset="reactive(props.rootOffset)"
                :scale="props.scale"
                :position="position"
                :selected="commentStore.getCommentMultiSelected(props.comment.id)"
                class="draggable-pan"
                @move="onMove"
                @mouseup="saveText"
                @pan-by="(p) => emit('pan-by', p)" />
            <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
            <span
                ref="editableElement"
                :contenteditable="!props.readonly"
                class="prevent-zoom"
                spellcheck="false"
                :class="{
                    bold: props.comment.data.bold,
                    italic: props.comment.data.italic,
                }"
                @blur="saveText"
                @mouseup.stop
                @dblclick.prevent="onDoubleClick"
                v-html="escapeAndSanitize(props.comment.data.text)" />
        </div>

        <BButtonGroup v-if="!props.readonly" class="style-buttons">
            <BButton
                class="button font-weight-bold prevent-zoom"
                variant="outline-primary"
                :title="props.comment.data.bold ? '取消粗体' : '设为粗体'"
                :pressed="props.comment.data.bold"
                @click="toggleBold">
                B
            </BButton>
            <BButton
                class="button font-italic prevent-zoom"
                variant="outline-primary"
                :title="props.comment.data.italic ? '取消斜体' : '设为斜体'"
                :pressed="props.comment.data.italic"
                @click="toggleItalic">
                I
            </BButton>
            <BButton
                class="button prevent-zoom"
                variant="outline-primary"
                title="颜色"
                :pressed="showColorSelector"
                @click="() => (showColorSelector = !showColorSelector)">
                <FontAwesomeIcon icon="fa-palette" class="prevent-zoom" />
            </BButton>
            <BButton
                class="button prevent-zoom"
                variant="primary"
                :title="decreaseFontSizeTitle"
                @click="decreaseFontSize">
                <FontAwesomeIcon :icon="['gxd', 'textSmaller']" class="prevent-zoom" />
            </BButton>
            <BButton
                class="button prevent-zoom"
                variant="primary"
                :title="increaseFontSizeTitle"
                @click="increaseFontSize">
                <FontAwesomeIcon :icon="['gxd', 'textLarger']" class="prevent-zoom" />
            </BButton>
            <BButton class="button prevent-zoom" variant="dark" title="删除注释" @click="() => emit('remove')">
                <FontAwesomeIcon icon="far fa-trash-alt" class="prevent-zoom" />
            </BButton>
        </BButtonGroup>

        <ColorSelector
            v-if="showColorSelector"
            class="color-selector"
            :color="props.comment.color"
            @set-color="onSetColor" />
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
@import "buttonGroup.scss";

.text-workflow-comment {
    position: absolute;
    width: 100%;
    height: 100%;

    .resize-container {
        z-index: 200;
    }

    &:focus-within {
        .style-buttons {
            visibility: visible;
        }

        .color-selector {
            visibility: visible;
        }

        .resize-container {
            resize: both;
            border-color: $brand-primary;
        }
    }

    .style-buttons {
        visibility: hidden;
        @include button-group-style;
    }
}

.resize-container {
    --font-size: 1rem;
    --font-color: #{$brand-primary};

    color: var(--font-color);
    font-size: var(--font-size);

    width: 100%;
    height: 100%;

    min-height: calc(1em + 10px);
    min-width: calc(1em + 20px);

    border-color: transparent;
    border-radius: 0.25rem;
    border-width: 2px;
    border-style: solid;

    overflow: hidden;

    position: absolute;

    span {
        position: absolute;
        margin: 5px 10px;
        line-height: 1;

        &.bold {
            font-weight: 700;
        }

        &.italic {
            font-style: italic;
        }

        &:focus,
        &:focus-visible {
            border: none;
            outline: none;
        }
    }

    .draggable-pan {
        cursor: move;
        position: absolute;
        width: 100%;
        height: 100%;
        top: 0;
    }

    &.resizable:focus-within,
    &.resizable:focus {
        resize: both;
        border-color: $brand-primary;
    }

    &.multi-selected {
        box-shadow: 0 0 0 2px $white, 0 0 0 4px lighten($brand-info, 20%);
    }
}

.color-selector {
    visibility: hidden;
    right: 0.75rem;
    top: -4.5rem;
}
</style>
