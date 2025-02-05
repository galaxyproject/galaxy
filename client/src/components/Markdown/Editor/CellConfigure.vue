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
        <div class="d-flex justify-content-end">
            <BButton variant="outline-primary" class="mr-2" @click="$emit('cancel')">Cancel</BButton>
            <BButton variant="outline-primary">OK</BButton>
        </div>
    </div>
</template>

<script setup lang="ts">
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import ConfigureGalaxy from "./configurations/ConfigureGalaxy.vue";

defineProps<{
    name: string;
    content: string;
}>();

defineEmits<{
    (e: "cancel"): void;
    (e: "change", content: string): void;
}>();
</script>
