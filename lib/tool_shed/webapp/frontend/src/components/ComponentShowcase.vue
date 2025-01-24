<script setup lang="ts">
import { useAttrs } from "vue"

const attrs = useAttrs()
</script>

<template>
    <q-card flat bordered class="q-my-lg">
        <q-card-section>
            <div class="text-h6">{{ attrs.title }}</div>
        </q-card-section>
        <q-separator horizontal />
        <slot></slot>
    </q-card>
</template>
