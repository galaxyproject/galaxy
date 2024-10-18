<script setup lang="ts">
import { faCog, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup, BDropdown, BDropdownForm, BDropdownItemButton, BFormCheckbox } from "bootstrap-vue";
//@ts-ignore deprecated package without types (vue 2, remove this comment on vue 3 migration)
import { ArrowLeftFromLine, ArrowRightToLine } from "lucide-vue";
import { computed } from "vue";

import { useWorkflowNodeInspectorStore } from "@/stores/workflowNodeInspectorStore";
import type { Step } from "@/stores/workflowStepStore";

import FormTool from "./Forms/FormTool.vue";
import DraggableSeparator from "@/components/Common/DraggableSeparator.vue";
import Heading from "@/components/Common/Heading.vue";
import IdleLoad from "@/components/Common/IdleLoad.vue";

const props = defineProps<{
    step: Step;
    datatypes: string[];
}>();

const emit = defineEmits<{
    (e: "postJobActionsChanged", id: string, postJobActions: unknown): void;
    (e: "annotationChanged", id: string, annotation: string): void;
    (e: "labelChanged", id: string, label: string): void;
    (e: "dataChanged", id: string, data: unknown): void;
    (e: "stepUpdated", id: string, step: Step): void;
    (e: "close"): void;
}>();

const inspectorStore = useWorkflowNodeInspectorStore();

const maximized = computed(() => inspectorStore.maximized(props.step));
const width = computed(() => inspectorStore.width(props.step));

const cssVars = computed(() => ({
    "--width": `${width.value}px`,
}));

const isTool = computed(() => props.step.type === "tool");

const title = computed(() => `${props.step.id + 1}: ${props.step.label ?? props.step.name}`);

function close() {
    inspectorStore.generalMaximized = false;
    emit("close");
}
</script>

<template>
    <section class="tool-inspector" :class="{ maximized }" :style="cssVars">
        <DraggableSeparator
            v-if="!maximized"
            inner
            :position="width"
            side="right"
            :min="100"
            :max="1200"
            @positionChanged="(v) => inspectorStore.setWidth(props.step, v)"></DraggableSeparator>

        <div class="inspector-heading">
            <Heading h2 inline size="sm"> {{ title }} </Heading>

            <BButtonGroup>
                <BButton
                    v-if="!maximized"
                    class="heading-button"
                    variant="link"
                    size="md"
                    @click="inspectorStore.setMaximized(props.step, true)">
                    <ArrowLeftFromLine absolute-stroke-width :size="17" />
                </BButton>
                <BButton
                    v-else
                    class="heading-button"
                    variant="link"
                    size="md"
                    @click="inspectorStore.setMaximized(props.step, false)">
                    <ArrowRightToLine absolute-stroke-width :size="17" />
                </BButton>

                <BDropdown class="dropdown" toggle-class="heading-button" variant="link" size="md" no-caret>
                    <template v-slot:button-content>
                        <FontAwesomeIcon :icon="faCog" fixed-width />
                    </template>

                    <BDropdownForm form-class="px-2" title="remember size for all steps using this tool">
                        <BFormCheckbox
                            :checked="inspectorStore.isStored(props.step)"
                            @input="(v) => inspectorStore.setStored(props.step, v)">
                            remember size
                        </BFormCheckbox>
                    </BDropdownForm>

                    <BDropdownItemButton @click="inspectorStore.clearAllStored">
                        reset all stored sizes
                    </BDropdownItemButton>
                </BDropdown>

                <BButton class="heading-button" variant="link" size="md" @click="close">
                    <FontAwesomeIcon :icon="faTimes" fixed-width />
                </BButton>
            </BButtonGroup>
        </div>

        <div class="inspector-content">
            <IdleLoad :key="props.step.id" spinner center class="w-100 h-50">
                <FormTool
                    v-if="isTool"
                    class="w-100"
                    :step="props.step"
                    :datatypes="props.datatypes"
                    @onSetData="(id, d) => emit('dataChanged', id, d)"
                    @onUpdateStep="(id, s) => emit('stepUpdated', id, s)"
                    @onChangePostJobActions="(id, a) => emit('postJobActionsChanged', id, a)"
                    @onAnnotation="(id, a) => emit('annotationChanged', id, a)"
                    @onLabel="(id, l) => emit('labelChanged', id, l)"></FormTool>
            </IdleLoad>
        </div>
    </section>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.tool-inspector {
    --clearance: 8px;
    --width: 300px;

    position: absolute;
    right: 0;
    top: var(--clearance);
    bottom: var(--clearance);
    // add border width to node draggable separators width
    width: calc(var(--width) + 1px);
    max-width: calc(100% - var(--clearance));

    overflow: hidden;

    background-color: $white;

    z-index: 50000;
    border-color: $border-color;
    border-width: 1px;
    border-style: solid;
    border-radius: 0.5rem 0 0 0.5rem;
    display: flex;
    flex-direction: column;

    &.maximized {
        border-radius: 0.5rem;
        --clearance: 16px;
        right: var(--clearance);
        top: var(--clearance);
        bottom: var(--clearance);
        left: var(--clearance);
        width: calc(100% - var(--clearance) * 2);
    }

    .inspector-heading {
        padding: 0.25rem 0.5rem;
        display: flex;
        justify-content: space-between;

        h2 {
            word-break: break-word;
        }

        &:deep(.heading-button) {
            padding: 0.4rem;
            display: grid;
            place-items: center;
        }

        .dropdown.show {
            display: inline-flex;
        }
    }

    .inspector-content {
        overflow-y: auto;
        padding: 0.5rem 0.5rem;
        padding-top: 0;
    }
}
</style>
