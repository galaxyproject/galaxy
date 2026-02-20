<script setup lang="ts">
import type { ExecutionState } from "./types";

const props = defineProps<{
    state: ExecutionState;
}>();
</script>

<template>
    <div class="pyodide-status card mt-2">
        <div class="card-body">
            <div v-if="props.state.status === 'initialising'" class="text-muted">Preparing browser environment…</div>
            <div v-else-if="props.state.status === 'installing'" class="text-muted">Installing Python packages…</div>
            <div v-else-if="props.state.status === 'fetching'" class="text-muted">Downloading datasets…</div>
            <div v-else-if="props.state.status === 'running'" class="text-muted">
                Running generated Python in the browser…
            </div>
            <div v-else-if="props.state.status === 'submitting'" class="text-muted">
                Sending results back to Galaxy…
            </div>
            <div v-else-if="props.state.status === 'completed'" class="text-success">
                Execution completed in your browser.
            </div>
            <div v-else-if="props.state.status === 'error'" class="text-danger">
                Execution failed{{ props.state.errorMessage ? ": " + props.state.errorMessage : "" }}
            </div>

            <div v-if="props.state.stdout" class="mt-2">
                <h6 class="mb-1">Stdout</h6>
                <pre class="pyodide-stream">
                        {{ props.state.stdout }}
                    </pre
                >
            </div>
            <div v-if="props.state.stderr" class="mt-2">
                <h6 class="mb-1 text-danger">Stderr</h6>
                <pre class="pyodide-stream text-danger">
                        {{ props.state.stderr }}
                    </pre
                >
            </div>
            <div v-if="props.state.artifacts.length" class="mt-2">
                <h6 class="mb-1">Artifacts</h6>
                <div class="artifact-grid">
                    <div
                        v-for="artifact in props.state.artifacts"
                        :key="artifact.dataset_id || artifact.name"
                        class="artifact-grid-item">
                        <div class="artifact-name">
                            {{ artifact.name || artifact.dataset_id }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/chat-gxy-artifacts.scss";

.pyodide-status {
    border: 1px dashed #6c757d;
    background: #f8f9fa;

    .pyodide-stream {
        background: #1e1e1e;
        color: #f8f9fa;
        padding: 0.5rem;
        border-radius: 4px;
        max-height: 200px;
        overflow: auto;
        font-family: var(--font-family-monospace);
        font-size: 0.85rem;

        &.text-danger {
            color: #f8d7da;
        }
    }
}
</style>
