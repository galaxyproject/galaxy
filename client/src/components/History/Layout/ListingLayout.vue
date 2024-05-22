<script setup lang="ts">
import { nextTick, ref, watch } from "vue";

import IntersectionObservable from "./IntersectionObservable.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const props = defineProps<{
    items: any[];
    queryKey?: string;
    dataKey?: string;
    loading?: boolean;
    offset?: number;
}>();

const emit = defineEmits<{
    (e: "scroll", currentOffset: number): void;
}>();

const root = ref<HTMLDivElement>();
const currentOffset = ref(0);

watch(
    () => currentOffset.value,
    (offset) => emit("scroll", offset)
);

watch(
    () => props.queryKey,
    () => {
        root.value?.scrollTo({
            top: 0,
        });
    }
);

watch(
    () => props.offset,
    async (offset) => {
        await nextTick();
        if (offset !== undefined) {
            scrollToOffset(offset);
        }
    },
    { immediate: true }
);

function scrollToOffset(offset: number) {
    const element = root.value?.querySelector(`.listing-layout-item[data-index="${offset}"]`);
    element?.scrollIntoView();
}

const observer = new IntersectionObserver(
    (items) => {
        const intersecting = items.filter((item) => item.isIntersecting);
        const indices = intersecting.map((item) => parseInt(item.target.getAttribute("data-index") ?? "0"));
        currentOffset.value = indices.length > 0 ? Math.min(...indices) : 0;
    },
    { root: root.value }
);

function getKey(item: unknown, index: number) {
    if (props.dataKey) {
        return (item as Record<string, unknown>)[props.dataKey];
    } else {
        return index;
    }
}
</script>

<template>
    <div ref="root" class="listing-layout">
        <IntersectionObservable
            v-for="(item, i) in props.items"
            :key="getKey(item, i)"
            class="listing-layout-item"
            :data-index="i"
            :observer="observer">
            <slot name="item" :item="item" :current-offset="i" />
        </IntersectionObservable>
        <LoadingSpan v-if="props.loading" class="m-2" message="Loading" />
    </div>
</template>

<style scoped lang="scss">
.listing-layout {
    position: absolute;
    width: 100%;
    height: 100%;
    overflow-y: scroll;
}
</style>
