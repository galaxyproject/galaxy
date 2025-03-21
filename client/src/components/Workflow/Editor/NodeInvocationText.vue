<script setup lang="ts">
import { faCheckSquare, faSquare } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormInput } from "bootstrap-vue";
import { sanitize } from "dompurify";

import { isWorkflowInput } from "@/components/Workflow/constants";
import { type GraphStep, iconClasses, statePlaceholders } from "@/composables/useInvocationGraph";

const props = defineProps<{
    invocationStep: GraphStep;
}>();

function isColor(value?: string): boolean {
    return value ? value.match(/^#[0-9a-f]{6}$/i) !== null : false;
}

function textHtml(value: string): string {
    return sanitize(value, { ALLOWED_TAGS: ["b"] });
}
</script>
<template>
    <div class="p-1 unselectable">
        <div v-if="props.invocationStep.jobs">
            <div v-for="(value, key) in props.invocationStep.jobs" :key="key">
                <span v-if="value !== undefined" class="d-flex align-items-center">
                    <FontAwesomeIcon
                        v-if="iconClasses[key]"
                        :icon="iconClasses[key]?.icon"
                        :class="iconClasses[key]?.class"
                        :spin="iconClasses[key]?.spin"
                        size="sm"
                        class="mr-1" />
                    {{ value }} 个作业{{ value > 1 ? "s" : "" }} {{ statePlaceholders[key] || key }}。
                </span>
            </div>
        </div>
        <div v-else-if="isWorkflowInput(props.invocationStep.type)" class="truncate w-100">
            <span v-if="typeof props.invocationStep.nodeText === 'boolean'">
                <FontAwesomeIcon :icon="props.invocationStep.nodeText ? faCheckSquare : faSquare" />
                {{ props.invocationStep.nodeText }}
            </span>
            <span v-else-if="isColor(props.invocationStep.nodeText)" class="d-flex align-items-center">
                <i> {{ props.invocationStep.nodeText }}: </i>
                <BFormInput
                    :value="props.invocationStep.nodeText"
                    class="ml-1 p-0 color-input"
                    type="color"
                    size="sm"
                    readonly />
            </span>
            <!-- eslint-disable vue/no-v-html -->
            <span
                v-else-if="props.invocationStep.nodeText !== undefined"
                v-html="textHtml(props.invocationStep.nodeText)" />
            <span v-else>这是一个输入</span>
        </div>
        <div v-else-if="props.invocationStep.type === 'subworkflow'">这是一个子工作流。</div>
        <div v-else>此步骤尚无作业。</div>
    </div>
</template>

<style scoped>
.truncate {
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;

    .color-input {
        max-height: 1rem;
    }
}
</style>
