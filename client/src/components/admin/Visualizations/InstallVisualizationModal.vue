<template>
    <b-modal
        :visible="show"
        title="Install Visualization"
        :ok-disabled="!visualizationId || installing"
        :ok-title="installing ? 'Installing...' : 'Install'"
        @hidden="emit('cancel')"
        @ok="handleInstall">
        <div v-if="installing" class="text-center">
            <b-spinner label="Installing..." />
            <p class="mt-2">Installing visualization package...</p>
            <p class="small text-muted">This may take a few minutes...</p>
        </div>

        <div v-else-if="packageData">
            <div class="mb-3">
                <h5>{{ packageData.name }}</h5>
                <p v-if="packageData.description" class="text-muted">{{ packageData.description }}</p>
                <div class="small"><strong>Version:</strong> {{ packageData.version }}</div>
            </div>

            <b-form-group
                label="Visualization ID:"
                label-for="viz-id-input"
                description="Choose a unique identifier for this visualization in Galaxy">
                <b-form-input
                    id="viz-id-input"
                    v-model="visualizationId"
                    :placeholder="suggestedId"
                    :state="visualizationId ? (isValidId ? true : false) : null" />
                <b-form-invalid-feedback v-if="!isValidId">
                    ID must contain only letters, numbers, and underscores
                </b-form-invalid-feedback>
            </b-form-group>

            <BAlert v-if="idConflict" variant="warning" show>
                <FontAwesomeIcon :icon="faExclamationTriangle" class="mr-1" />
                A visualization with this ID is already installed. Installing will replace it.
            </BAlert>
        </div>
    </b-modal>
</template>

<script setup lang="ts">
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { AvailableVisualization, Visualization } from "./services";

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
    (e: "confirm", visualizationId: string): void;
    (e: "cancel"): void;
}>();

const visualizationId = ref("");

const suggestedId = computed(() => {
    if (!props.packageData) {
        return "";
    }
    const name = props.packageData.name.includes("/")
        ? props.packageData.name.split("/").pop()!
        : props.packageData.name;
    return name.replace(/[^a-zA-Z0-9_]/g, "_");
});

const isValidId = computed(() => {
    return /^[a-zA-Z0-9_]+$/.test(visualizationId.value);
});

const idConflict = computed(() => {
    return props.installedVisualizations?.some((viz) => viz.id === visualizationId.value);
});

watch(
    () => props.show,
    (isShown) => {
        if (isShown && props.packageData) {
            visualizationId.value = suggestedId.value;
        } else if (!isShown) {
            visualizationId.value = "";
        }
    },
);

function handleInstall() {
    if (visualizationId.value && isValidId.value) {
        emit("confirm", visualizationId.value);
    }
}
</script>
