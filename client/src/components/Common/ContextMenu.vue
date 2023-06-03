<script setup lang="ts">
import { computed, ref, watch, type Ref } from "vue";

interface Position {
    left: string;
    top: string;
}

interface Props {
    visible: boolean;
    x: number;
    y: number;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "hide"): void;
}>();

const placeContextMenu: Ref<Position> = ref({ left: "", top: "" });

watch(
    () => [props.x, props.y],
    () => {
        placeContextMenu.value.left = `${props.x}px`;
        placeContextMenu.value.top = `${props.y}px`;
    }
);
</script>

<template>
    <div v-if="visible">
        <div class="context-overlay" @click="emit('hide')" />
        <b-card class="context-menu" :style="placeContextMenu">
            <slot />
        </b-card>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.context-menu {
    position: fixed;
    background: $panel-bg-color;
    z-index: 11;
}

.context-overlay {
    position: fixed;
    left: 0;
    top: 0;
    height: 100%;
    width: 100%;
    z-index: 10;
}
</style>
