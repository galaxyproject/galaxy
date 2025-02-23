<template>
    <BButton
        v-b-tooltip.right
        class="border-0 m-1 px-1 py-0"
        :class="{ active }"
        :title="title"
        :variant="active ? 'outline-secondary' : 'outline-primary'"
        @click="onClick()"
        @mouseleave="onMouseLeave($event)">
        <slot />
    </BButton>
</template>

<script setup lang="ts">
import { BButton } from "bootstrap-vue";

withDefaults(
    defineProps<{
        title: string;
        active: boolean;
    }>(),
    {
        active: false,
    }
);

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
