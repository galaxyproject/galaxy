<script setup lang="ts">
defineProps({
    title: {
        type: String,
        required: true,
    },
    description: {
        type: String,
        default: "",
    },
})
</script>
<template>
    <span>
        <q-item class="fit">
            <q-item-section>
                <q-item-label caption>{{ title }}</q-item-label>
                <q-item-label v-if="description" caption class="text-grey-6">{{ description }}</q-item-label>
            </q-item-section>
        </q-item>
        <q-separator horizontal />
        <q-card-section vertical>
            <slot></slot>
        </q-card-section>
    </span>
</template>
