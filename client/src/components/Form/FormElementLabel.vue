<script setup lang="ts">
import { faCheck } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

withDefaults(
    defineProps<{
        help?: string;
        required?: boolean;
        title: string;
        condition?: boolean;
    }>(),
    {
        condition: true,
        required: false,
    }
);
</script>

<template>
    <div>
        <div v-localize class="font-weight-bold py-2">
            <span>{{ title }}</span>
            <FontAwesomeIcon v-if="condition && required" class="text-success" :icon="faCheck" />
            <span v-else-if="required" class="text-danger">*</span>
        </div>
        <slot />
        <small v-localize class="text-muted py-2">{{ help }}</small>
    </div>
</template>
