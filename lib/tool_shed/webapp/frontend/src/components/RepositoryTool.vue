<script setup lang="ts">
import type { RepositoryTool } from "@/schema"

interface RepositoryToolProps {
    tool: RepositoryTool
}

defineProps<RepositoryToolProps>()
</script>

<template>
    <q-item>
        <q-item-section class="q-pa-sm" top>
            <q-item-label lines="1">
                <span class="text-weight-medium">{{ tool.name }}</span>
            </q-item-label>
            <q-item-label caption lines="1">
                {{ tool.description }}
            </q-item-label>
            <q-item-label lines="1" class="q-mt-xs text-body2 text-weight-bold text-primary text-uppercase">
                <code>{{ tool.id }} / {{ tool.version }}</code>
            </q-item-label>
        </q-item-section>
    </q-item>
</template>
