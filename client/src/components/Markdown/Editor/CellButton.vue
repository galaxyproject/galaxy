<template>
    <BButton
        v-b-tooltip.right
        class="border-0 m-1 px-1 py-0"
        :title="title"
        variant="outline-primary"
        @click.stop="onClick()"
        @mouseleave="onMouseLeave($event)">
        <slot />
    </BButton>
</template>

<script setup lang="ts">
import { BButton } from "bootstrap-vue";

defineProps<{
    title: string;
}>();

const emit = defineEmits<{
    (e: "click"): void;
}>();

function onMouseLeave(event: Event) {
    const target = event.target as HTMLElement;
    target.blur();
}

function onClick() {
    emit("click");
}
</script>
