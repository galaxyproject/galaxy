<script setup lang="ts">
import { computed, ref } from "vue";

import type { Rectangle } from "@/components/Workflow/Editor/modules/geometry";
import { wait } from "@/utils/utils";

const bounds = ref<Rectangle>({ x: 0, y: 0, width: 0, height: 0 });
const blink = ref(false);

const style = computed(() => {
    console.log("computed");

    return {
        top: bounds.value.y + "px",
        left: bounds.value.x + "px",
        width: bounds.value.width + "px",
        height: bounds.value.height + "px",
    };
});

async function show(area: Rectangle) {
    bounds.value = area;
    blink.value = false;
    await wait(100);
    blink.value = true;
}

defineExpose({
    show,
});
</script>

<template>
    <div class="area-highlight" :class="{ blink }" :style="style"></div>
</template>

<style lang="scss" scoped>
.area-highlight {
    pointer-events: none;
    position: absolute;

    z-index: 10000;

    &::before {
        content: "";
        display: block;
        position: absolute;
        top: calc(var(--spacing-2) * -1);
        left: calc(var(--spacing-2) * -1);
        bottom: calc(var(--spacing-2) * -1);
        right: calc(var(--spacing-2) * -1);

        border-width: var(--spacing-1);
        border-radius: var(--spacing-2);
        border-color: var(--color-green-500);
        border-style: solid;

        opacity: 0;

        @keyframes blink {
            from {
                opacity: 1;
            }

            40% {
                opacity: 0;
            }

            60% {
                opacity: 1;
            }

            to {
                opacity: 0;
            }
        }
    }

    &.blink {
        &::before {
            animation: blink 1s step-end;
        }
    }
}
</style>
