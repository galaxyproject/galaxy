<script setup lang="ts">
import CenterFrame from "@/entry/analysis/modules/CenterFrame.vue";

interface Props {
    datasetId: string;
    isPreview: boolean;
}

const props = withDefaults(defineProps<Props>(), {});
</script>

<template>
    <CenterFrame
        :src="`/datasets/${props.datasetId}/display/?preview=True`"
        :is-preview="true"
        @load="$emit('load')" />
</template>

