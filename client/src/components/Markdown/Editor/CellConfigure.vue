<template>
    <div class="p-4 bg-white mb-2">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <div>
                <div class="h2">Attach Data</div>
                <div class="small">Fill in the fields below to map required inputs to this cell.</div>
            </div>
            <BButton variant="link" class="align-self-start" @click="$emit('cancel')">
                <FontAwesomeIcon :icon="faTimes" class="fa-lg" />
            </BButton>
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
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

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
