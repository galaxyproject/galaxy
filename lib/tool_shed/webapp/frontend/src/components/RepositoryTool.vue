<script setup lang="ts">
import type { RepositoryTool } from "@/schema"

interface RepositoryToolProps {
    tool: RepositoryTool
    changesetRevision: string
    trsToolId?: string
}

defineProps<RepositoryToolProps>()
</script>

<template>
    <q-item>
        <q-item-section class="q-pa-sm" top>
            <q-item-label lines="1">
                <router-link
                    v-if="trsToolId"
                    class="text-primary text-bold text-body1"
                    :to="`/tools/${trsToolId}/versions/${tool.version}?from_changeset_revision=${changesetRevision}`"
                >
                    {{ tool.name }}
                </router-link>
                <span v-else>
                    {{ tool.name }}
                </span>
                <span class="q-mt-xs text-body2 text-weight-bold text-primary text-uppercase">
                    (<code>{{ tool.id }} / {{ tool.version }}</code
                    >)
                </span>
            </q-item-label>
            <q-item-label caption lines="1">
                {{ tool.description }}
            </q-item-label>
        </q-item-section>
    </q-item>
</template>
