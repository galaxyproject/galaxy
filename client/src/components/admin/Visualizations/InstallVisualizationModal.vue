<template>
    <GModal
        :show="show"
        title="Install Visualization"
        confirm
        :close-on-ok="false"
        :ok-disabled="!isValidId || idConflict || installing"
        :ok-text="installing ? 'Installing...' : 'Install'"
        :cancel-disabled="installing"
        @close="emit('cancel')"
        @ok="handleInstall">
        <div v-if="installing" class="text-center">
            <LoadingSpan message="Installing visualization package" />
            <p class="small text-muted mt-2">This may take a few minutes...</p>
        </div>

        <div v-else-if="packageData">
            <div class="mb-3">
                <h5>{{ packageData.name }}</h5>
                <p v-if="packageData.description" class="text-muted">{{ packageData.description }}</p>
                <div class="small"><strong>Version:</strong> {{ packageData.version }}</div>
            </div>

            <p class="mb-2">
                Installs under the package name without its scope:
                <code>{{ visualizationId }}</code>
            </p>
            <GAlert v-if="!isValidId" variant="danger">
                <code>{{ visualizationId }}</code> can't be a visualization ID: only letters, numbers, hyphens and
                underscores are allowed.
            </GAlert>

            <GAlert v-if="idConflict" variant="warning">
                <FontAwesomeIcon :icon="faExclamationTriangle" class="mr-1" />
                A visualization with this ID is already installed. Use Update on its card to change versions.
            </GAlert>
        </div>
    </GModal>
</template>

<script setup lang="ts">
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { AvailableVisualization, Visualization } from "./services";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    show?: boolean;
    packageData?: AvailableVisualization | null;
    installing?: boolean;
    installedVisualizations?: Visualization[];
}

const props = withDefaults(defineProps<Props>(), {
    show: false,
    packageData: null,
    installing: false,
    installedVisualizations: () => [],
});

const emit = defineEmits<{
    (e: "confirm"): void;
    (e: "cancel"): void;
}>();

// The server installs every package under its unscoped name; this just previews that id.
const visualizationId = computed(() => props.packageData?.name.split("/").pop() ?? "");

const isValidId = computed(() => /^[a-zA-Z0-9_-]+$/.test(visualizationId.value));

const idConflict = computed(() => props.installedVisualizations.some((viz) => viz.id === visualizationId.value));

function handleInstall() {
    if (isValidId.value && !idConflict.value) {
        emit("confirm");
    }
}
</script>
