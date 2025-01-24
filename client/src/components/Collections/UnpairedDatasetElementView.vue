<script setup lang="ts">
import { computed, ref } from "vue";

import type { HDASummary } from "@/api";
import { useAnimationFrameSize } from "@/composables/sensors/animationFrameSize";

interface Props {
    element: HDASummary;
    disabled?: boolean;
    showExtension?: boolean;
    showHid?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    disabled: false,
    showExtension: true,
    showHid: true,
});

const emit = defineEmits<{
    (event: "element-is-selected", element: HDASummary): void;
}>();

const unpairedElement = ref<HTMLElement | null>(null);
const elementName = ref<HTMLElement | null>(null);

const { width: parentWidth } = useAnimationFrameSize(unpairedElement);

const childWidth = computed(() => elementName.value?.clientWidth);
const shouldMoveElement = computed(() => {
    if (childWidth.value && parentWidth.value && childWidth.value <= parentWidth.value) {
        return false;
    } else {
        return true;
    }
});

function getExtension(): string {
    return "extension" in props.element && props.element.extension ? props.element.extension : "";
}
</script>

<template>
    <li
        ref="unpairedElement"
        class="dataset unpaired"
        :class="{ disabled: props.disabled }"
        :aria-disabled="props.disabled"
        role="button"
        tabindex="0"
        @keydown.enter="emit('element-is-selected', props.element)"
        @click="emit('element-is-selected', props.element)">
        <span ref="elementName" class="element-name" :class="{ moves: shouldMoveElement }">
            <span v-if="props.element.hid && props.showHid">{{ props.element.hid }}:</span>
            <strong>{{ props.element.name }}</strong>
            <i v-if="props.element.extension && props.showExtension"> ({{ getExtension() }}) </i>
        </span>
    </li>
</template>

<style scoped>
.disabled {
    pointer-events: none;
    opacity: 0.5;
}
</style>
