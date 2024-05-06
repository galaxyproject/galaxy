<script setup lang="ts">
import { ref, watch } from "vue";

import { useUndoRedoStore } from "@/stores/undoRedoStore";

const props = defineProps<{
    storeId: string;
}>();

const currentStore = ref(useUndoRedoStore(props.storeId));

watch(
    () => props.storeId,
    (id) => (currentStore.value = useUndoRedoStore(id))
);
</script>

<template>
    <section class="undo-redo-stack">
        <div class="scroll-list">
            <button
                v-for="action in currentStore.redoActionStack"
                :key="action.id"
                @click="currentStore.rollForwardTo(action)">
                {{ action.name }}
            </button>

            <span> current state </span>

            <button
                v-for="action in [...currentStore.undoActionStack].reverse()"
                :key="action.id"
                @click="currentStore.rollBackTo(action)">
                {{ action.name }}
            </button>
        </div>
    </section>
</template>

<style scoped lang="scss">
.undo-redo-stack {
    width: 100%;

    .scroll-list {
        display: flex;
        flex-direction: column;
    }
}
</style>
