<script setup lang="ts">
interface PageContainerProps {
    baseClass?: string
}

withDefaults(defineProps<PageContainerProps>(), {
    baseClass: "q-pa-md",
})
</script>
<template>
    <q-page :class="baseClass">
        <slot></slot>
    </q-page>
</template>
