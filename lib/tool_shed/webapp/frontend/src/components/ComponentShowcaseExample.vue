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
    <div class="component-showcase-example">
        <q-item class="fit">
            <q-item-section>
                <q-item-label caption>{{ title }}</q-item-label>
                <q-item-label v-if="description" caption class="text-grey-6">{{ description }}</q-item-label>
            </q-item-section>
        </q-item>
        <hr />
        <div class="component-showcase-example-body">
            <slot></slot>
        </div>
    </div>
</template>

<style scoped>
.component-showcase-example-body {
    display: flex;
    flex-direction: column;
    padding: var(--spacing-4);
}
</style>
