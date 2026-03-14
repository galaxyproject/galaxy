<script setup lang="ts">
import { ref } from "vue";

import type { ChatMessage } from "./types";
import { downloadArtifact, formatSize } from "./utilities";

import Heading from "@/components/Common/Heading.vue";

const props = defineProps<{
    message: ChatMessage & {
        artifacts: NonNullable<ChatMessage["artifacts"]>;
    };
}>();

const toggled = ref(false);
</script>

<template>
    <div class="mt-2">
        <div class="artifacts-panel">
            <Heading h4 size="sm" separator :collapse="toggled ? 'closed' : 'open'" @click="toggled = !toggled">
                Saved Artifacts ({{ props.message.artifacts.length }})
            </Heading>
            <div v-if="!toggled" class="artifact-grid mt-2">
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
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/chat-gxy-artifacts.scss";

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
