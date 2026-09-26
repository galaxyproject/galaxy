<script setup lang="ts">
import { faColumns, faExpand } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref, watch } from "vue";

import GButton from "@/components/BaseComponents/GButton.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";

const props = defineProps<{
    documentationVisible: boolean;
}>();

const documentationWidth = ref(480);
const documentationExpanded = ref(false);
const documentationMounted = ref(props.documentationVisible);
const viewMode = computed(() => {
    if (!props.documentationVisible) {
        return "editor";
    }
    return documentationExpanded.value ? "documentation" : "split";
});

watch(
    () => props.documentationVisible,
    (visible) => {
        if (visible) {
            documentationMounted.value = true;
        } else {
            documentationExpanded.value = false;
        }
    },
);
</script>

<template>
    <div class="custom-tool-editor-workspace">
        <div class="custom-tool-workspace-content" :data-view-mode="viewMode">
            <section
                v-show="!documentationVisible || !documentationExpanded"
                class="custom-tool-editor-pane"
                aria-label="Tool editor">
                <slot name="editor" />
            </section>
            <FlexPanel
                v-if="documentationMounted || documentationVisible"
                v-show="documentationVisible"
                panel-id="custom-tool-documentation-panel"
                class="custom-tool-documentation-panel"
                :class="{ 'documentation-only': documentationExpanded }"
                side="right"
                :collapsible="false"
                :min-width="320"
                :max-width="800"
                :reactive-width.sync="documentationWidth">
                <div class="custom-tool-documentation-pane">
                    <div class="custom-tool-documentation-controls">
                        <GButton
                            transparent
                            icon-only
                            tooltip
                            size="small"
                            :title="documentationExpanded ? 'Show side by side' : 'Expand documentation'"
                            :aria-label="documentationExpanded ? 'Show side by side' : 'Expand documentation'"
                            :aria-pressed="documentationExpanded ? 'true' : 'false'"
                            data-description="toggle expanded documentation"
                            @click="documentationExpanded = !documentationExpanded">
                            <FontAwesomeIcon :icon="documentationExpanded ? faColumns : faExpand" />
                        </GButton>
                    </div>
                    <section class="custom-tool-documentation-content" aria-label="Tool documentation">
                        <slot name="documentation" />
                    </section>
                </div>
            </FlexPanel>
        </div>
    </div>
</template>

<style scoped>
.custom-tool-editor-workspace {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-height: 0;
}

.custom-tool-documentation-controls {
    display: flex;
    justify-content: flex-end;
    padding: var(--spacing-2) var(--spacing-2) 0;
}

.custom-tool-workspace-content {
    display: flex;
    flex: 1;
    min-height: 0;
    position: relative;
}

.custom-tool-editor-pane {
    flex: 1;
    min-height: 0;
    min-width: 0;
}

.custom-tool-documentation-pane {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
}

.custom-tool-documentation-content {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
}

.custom-tool-documentation-panel.documentation-only {
    border-left: 0;
    flex: 1;
    width: 100% !important;
}

.custom-tool-documentation-panel.documentation-only :deep(.drag-handle) {
    display: none;
}

@media (max-width: 768px) {
    .custom-tool-workspace-content[data-view-mode="split"] {
        flex-direction: column;
        overflow-y: auto;
    }

    .custom-tool-workspace-content[data-view-mode="split"] .custom-tool-editor-pane {
        flex: 0 0 50vh;
        min-height: 24rem;
    }

    .custom-tool-workspace-content[data-view-mode="split"] .custom-tool-documentation-panel.flex-panel {
        flex: 0 0 auto;
        min-height: 24rem;
        width: 100% !important;
    }

    .custom-tool-workspace-content[data-view-mode="split"] .custom-tool-documentation-panel :deep(.drag-handle) {
        display: none;
    }
}
</style>
