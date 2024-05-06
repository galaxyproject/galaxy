<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { useUndoRedoStore } from "@/stores/undoRedoStore";

import Heading from "@/components/Common/Heading.vue";

const props = defineProps<{
    storeId: string;
    heading?: string;
}>();

const heading = computed(() => props.heading ?? "Undo Redo Stack");

const currentStore = ref(useUndoRedoStore(props.storeId));

watch(
    () => props.storeId,
    (id) => (currentStore.value = useUndoRedoStore(id))
);
</script>

<template>
    <section class="undo-redo-stack">
        <Heading h2 size="sm"> {{ heading }} </Heading>
        <div class="scroll-list">
            <button v-for="action in currentStore.redoActionStack" :key="action.id">
                {{ action.name }}
            </button>

            <button v-for="action in currentStore.undoActionStack" :key="action.id">
                {{ action.name }}
            </button>
        </div>
    </section>
</template>

<style scoped lang="scss">
.undo-redo-stack {
}
</style>
