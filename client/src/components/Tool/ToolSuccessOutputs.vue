<script setup lang="ts">
import { faSignOutAlt } from "@fortawesome/free-solid-svg-icons";
import { computed } from "vue";

import type { JobResponse } from "@/api/jobs";

import DetailBlock from "@/components/Common/DetailBlock.vue";
import GenericItem from "@/components/History/Content/GenericItem.vue";

const props = defineProps<{
    jobResponse: JobResponse;
    collapsed: boolean;
}>();

const emit = defineEmits<{
    (e: "update:collapsed", value: boolean): void;
}>();

const outputs = computed(() => [
    ...(props.jobResponse?.outputs || []),
    ...(props.jobResponse?.output_collections || []),
]);
</script>

<template>
    <DetailBlock
        v-if="outputs.length"
        :collapsed="props.collapsed"
        :header-icon="faSignOutAlt"
        title="Tool Run Outputs"
        collapsible
        @update:collapsed="emit('update:collapsed', $event)">
        <div class="outputs-grid">
            <GenericItem
                v-for="output in outputs"
                :key="output.id"
                :item-id="output.id"
                :item-src="output.history_content_type === 'dataset' ? 'hda' : 'hdca'" />
        </div>
    </DetailBlock>
</template>

<style scoped lang="scss">
.outputs-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 0.5rem;
    padding: 0.5rem 0.25rem;
}
</style>
