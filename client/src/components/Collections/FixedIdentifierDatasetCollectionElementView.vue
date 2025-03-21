<script setup lang="ts">
import type { HDASummary } from "@/api";
import localize from "@/utils/localization";

import DatasetCollectionElementView from "./ListDatasetCollectionElementView.vue";

interface Props {
    element?: HDASummary;
    hasActions?: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
    (event: "element-is-discarded", element: HDASummary): void;
}>();
</script>

<template>
    <span>
        <DatasetCollectionElementView
            v-if="element"
            :key="element.id"
            :element="element"
            has-actions
            @element-is-discarded="emit('element-is-discarded', element)" />
        <div v-else class="collection-element alert-info">
            <i>{{ localize("未选择数据集") }}</i>
        </div>
    </span>
</template>
