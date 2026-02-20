<script setup lang="ts">
import type { Message } from "./types";
import { downloadArtifact, formatSize } from "./utilities";

const props = defineProps<{
    message: Message & {
        artifacts: NonNullable<Message["artifacts"]>;
    };
}>();
</script>

<template>
    <div class="mt-2">
        <details open class="artifacts-panel">
            <summary class="text-muted">Saved Artifacts ({{ props.message.artifacts.length }})</summary>
            <div class="artifact-grid">
                <div
                    v-for="artifact in props.message.artifacts"
                    :key="artifact.dataset_id || artifact.name"
                    class="artifact-grid-item">
                    <div class="artifact-name">
                        <button
                            v-if="artifact.download_url"
                            class="btn btn-link btn-sm p-0"
                            type="button"
                            @click="downloadArtifact(artifact)">
                            {{ artifact.name || artifact.dataset_id }}
                        </button>
                        <span v-else>{{ artifact.name || artifact.dataset_id }}</span>
                        <span v-if="artifact.size" class="text-muted ml-1"> ({{ formatSize(artifact.size) }}) </span>
                    </div>
                    <div
                        v-if="artifact.mime_type && artifact.mime_type.startsWith('image/') && artifact.download_url"
                        class="artifact-preview mt-2">
                        <img
                            :src="artifact.download_url"
                            :alt="artifact.name || 'plot preview'"
                            class="plot-preview img-thumbnail" />
                    </div>
                </div>
            </div>
        </details>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/chat-gxy-artifacts.scss";

.artifacts-panel summary {
    cursor: pointer;
    font-weight: 600;
}

.artifact-preview img {
    max-height: 180px;
    object-fit: contain;
}

.plot-preview {
    max-width: 320px;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    background: #fff;
    width: 100%;
}
</style>
