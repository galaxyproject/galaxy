<script setup lang="ts">
import type { AgentResponse } from "./types";

const props = defineProps<{
    metadata: NonNullable<AgentResponse["metadata"]>;
}>();
</script>

<template>
    <div class="executed-code">
        <details>
            <summary class="text-muted">Executed Python Code</summary>
            <pre>{{ props.metadata.executed_task?.code }}</pre>
        </details>
        <details v-if="props.metadata.stdout" class="mt-2">
            <summary class="text-muted">Execution Stdout</summary>
            <pre>{{ props.metadata.stdout }}</pre>
        </details>
        <details v-if="props.metadata.stderr" class="mt-2">
            <summary class="text-muted">Execution Stderr</summary>
            <pre class="text-danger">{{ props.metadata.stderr }}</pre>
        </details>
    </div>
</template>
