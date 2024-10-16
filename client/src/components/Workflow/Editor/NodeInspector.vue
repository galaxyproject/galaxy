<script setup lang="ts">
import { faCog, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup } from "bootstrap-vue";
//@ts-ignore deprecated package without types (vue 2, remove this comment on vue 3 migration)
import { ArrowLeftFromLine } from "lucide-vue";
import { computed, ref } from "vue";

import type { Step } from "@/stores/workflowStepStore";

import FormTool from "./Forms/FormTool.vue";
import DraggableSeparator from "@/components/Common/DraggableSeparator.vue";
import Heading from "@/components/Common/Heading.vue";

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
}>();

const width = ref(300);

const cssVars = computed(() => ({
    "--width": `${width.value}px`,
}));

const isTool = computed(() => props.step.type === "tool");

const title = computed(() => `${props.step.id + 1}: ${props.step.label ?? props.step.name}`);
</script>

<template>
    <section class="tool-inspector" :style="cssVars">
        <DraggableSeparator
            inner
            :position="width"
            side="right"
            :min="100"
            :max="1200"
            @positionChanged="(v) => (width = v)"></DraggableSeparator>

        <div class="inspector-heading">
            <Heading h2 inline size="sm"> {{ title }} </Heading>

            <BButtonGroup>
                <BButton variant="link" size="md">
                    <ArrowLeftFromLine absolute-stroke-width size="17" />
                </BButton>
                <BButton variant="link" size="md">
                    <FontAwesomeIcon :icon="faCog" fixed-width />
                </BButton>
                <BButton variant="link" size="md">
                    <FontAwesomeIcon :icon="faTimes" fixed-width />
                </BButton>
            </BButtonGroup>
        </div>

        <div class="inspector-content">
            <FormTool
                v-if="isTool"
                :step="props.step"
                :datatypes="props.datatypes"
                @onSetData="(id, d) => emit('dataChanged', id, d)"
                @onUpdateStep="(id, s) => emit('stepUpdated', id, s)"
                @onChangePostJobActions="(id, a) => emit('postJobActionsChanged', id, a)"
                @onAnnotation="(id, a) => emit('annotationChanged', id, a)"
                @onLabel="(id, l) => emit('labelChanged', id, l)"></FormTool>
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

    .inspector-heading {
        padding: 0.5rem;
        display: flex;
        justify-content: space-between;

        button {
            padding: 0.4rem;
            display: grid;
            place-items: center;
        }
    }

    .inspector-content {
        overflow-y: auto;
        height: 100%;
        padding: 0.5rem 0.5rem;
        padding-top: 0;
    }
}
</style>
