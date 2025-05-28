<template>
    <b-modal
        :visible="show"
        title="Install Visualization"
        :ok-disabled="!visualizationId || installing"
        :ok-title="installing ? 'Installing...' : 'Install'"
        @hidden="$emit('cancel')"
        @ok="handleInstall">
        <div v-if="installing" class="text-center">
            <b-spinner label="Installing..."></b-spinner>
            <p class="mt-2">Installing visualization package...</p>
            <p class="small text-muted">This may take a few minutes...</p>
        </div>

        <div v-else-if="visualization">
            <div class="mb-3">
                <h5>{{ visualization.name }}</h5>
                <p v-if="visualization.description" class="text-muted">{{ visualization.description }}</p>
                <div class="small"><strong>Version:</strong> {{ visualization.version }}</div>
            </div>

            <b-form-group
                label="Visualization ID:"
                label-for="viz-id-input"
                description="Choose a unique identifier for this visualization in Galaxy">
                <b-form-input
                    id="viz-id-input"
                    v-model="visualizationId"
                    :placeholder="suggestedId"
                    :state="visualizationId ? (isValidId ? true : false) : null"
                    @input="validateId"></b-form-input>
                <b-form-invalid-feedback v-if="!isValidId">
                    ID must contain only letters, numbers, and underscores
                </b-form-invalid-feedback>
            </b-form-group>

            <b-alert v-if="idConflict" variant="warning" show>
                <i class="fa fa-exclamation-triangle mr-1"></i>
                A visualization with this ID already exists and will be overwritten.
            </b-alert>
        </div>
    </b-modal>
</template>

<script>
export default {
    name: "InstallVisualizationModal",

    props: {
        show: {
            type: Boolean,
            default: false,
        },
        visualization: {
            type: Object,
            default: null,
        },
        installing: {
            type: Boolean,
            default: false,
        },
        installedVisualizations: {
            type: Array,
            default: () => [],
        },
    },

    data() {
        return {
            visualizationId: "",
        };
    },

    computed: {
        suggestedId() {
            if (!this.visualization) {
                return "";
            }
            // Extract name from scoped package (e.g., @galaxyproject/foo -> foo)
            const name = this.visualization.name.includes("/")
                ? this.visualization.name.split("/").pop()
                : this.visualization.name;
            return name.replace(/[^a-zA-Z0-9_]/g, "_");
        },

        isValidId() {
            return /^[a-zA-Z0-9_]+$/.test(this.visualizationId);
        },

        idConflict() {
            return this.installedVisualizations?.some((viz) => viz.id === this.visualizationId);
        },
    },

    watch: {
        show(isShown) {
            if (isShown && this.visualization) {
                this.visualizationId = this.suggestedId;
            } else if (!isShown) {
                this.visualizationId = "";
            }
        },
    },

    methods: {
        handleInstall() {
            if (this.visualizationId && this.isValidId) {
                this.$emit("confirm", this.visualizationId);
            }
        },

        validateId() {
            // Called on input change to trigger validation
        },
    },
};
</script>
