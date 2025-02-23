<template>
    <div class="bg-white my-2">
        <div class="d-flex justify-content-between align-items-center mb-2">
            <div>
                <div class="h3 mb-1">Attach Data</div>
                <div class="small">Fill in the fields below to map required inputs to this cell.</div>
            </div>
        </div>
        <ConfigureGalaxy v-if="name === 'galaxy'" :content="content" @change="$emit('change', $event)" />
        <ConfigureVisualization
            v-else-if="name === 'visualization'"
            :content="content"
            @change="$emit('change', $event)" />
        <b-alert v-else variant="warning" show> Data cannot be linked to this cell type. </b-alert>
    </div>
</template>

<script setup lang="ts">
import ConfigureGalaxy from "./Configurations/ConfigureGalaxy.vue";
import ConfigureVisualization from "./Configurations/ConfigureVisualization.vue";

defineProps<{
    name: string;
    content: string;
}>();

defineEmits<{
    (e: "cancel"): void;
    (e: "change", content: string): void;
}>();
</script>
