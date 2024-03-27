<script setup lang="ts">
import DatasetSource from "@/components/DatasetInformation/DatasetSource.vue";

interface Props {
    sources: {
        source_uri: string;
        transform: {
            action: "to_posix_lines" | "spaces_to_tabs" | "datatype_groom";
            datatype_ext: "bam" | "qname_sorted.bam" | "qname_input_sorted.bam" | "isa-tab" | "isa-json";
        }[];
    }[];
}

defineProps<Props>();
</script>

<template>
    <span class="dataset-sources">
        <ul class="dataset-sources-list">
            <DatasetSource v-for="(source, index) in sources" :key="index" :source="source" />
        </ul>
    </span>
</template>

<style scoped>
.dataset-sources-list {
    padding-inline-start: 20px;
    margin-bottom: 0px;
}
</style>
