<script setup lang="ts">
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
        <div class="font-weight-bold py-2">
            <span>{{ title }}</span>
            <small v-if="required && condition" class="align-top">*</small>
            <small v-else-if="required" class="text-danger">
                <span class="align-top">*</span>
                <small class="align-top">required</small>
            </small>
        </div>
        <slot />
        <small v-localize class="text-muted py-2">{{ help }}</small>
    </div>
</template>
