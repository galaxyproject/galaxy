<template>
    <div class="datatype-visualizations-manager">
        <h2>Datatype Visualization Mappings</h2>
        <p class="mb-4">
            Configure preferred visualizations for datatypes. These visualizations will be used as the default preview
            when viewing datasets of the specified type.
        </p>

        <!-- Loading state -->
        <div v-if="isLoading" class="text-center my-5">
            <font-awesome-icon icon="spinner" pulse size="2x" />
            <p class="mt-3">Loading datatype visualization mappings...</p>
        </div>

        <!-- Error message -->
        <BAlert v-if="error" show variant="danger" class="mb-4"> <strong>Error:</strong> {{ error }} </BAlert>

        <!-- Main content -->
        <div v-if="!isLoading && !error">
            <!-- Create new mapping form -->
            <BCard class="mb-4" header="Add New Mapping">
                <BForm @submit.prevent="addNewMapping">
                    <BFormGroup label="Datatype" label-for="new-datatype">
                        <BFormSelect
                            id="new-datatype"
                            v-model="newMapping.datatype"
                            :options="availableDatatypes"
                            required>
                            <template v-slot:first>
                                <BFormSelectOption :value="null">-- Select Datatype --</BFormSelectOption>
                            </template>
                        </BFormSelect>
                    </BFormGroup>

                    <BFormGroup label="Visualization" label-for="new-visualization">
                        <BFormSelect
                            id="new-visualization"
                            v-model="newMapping.visualization"
                            :options="availableVisualizations"
                            required>
                            <template v-slot:first>
                                <BFormSelectOption :value="null">-- Select Visualization --</BFormSelectOption>
                            </template>
                        </BFormSelect>
                    </BFormGroup>

                    <!-- Parameters section, can be expanded in the future -->
                    <BButton type="submit" variant="primary" :disabled="!isFormValid">Add Mapping</BButton>
                </BForm>
            </BCard>

            <!-- Existing mappings table -->
            <BCard header="Existing Mappings">
                <BTable
                    striped
                    hover
                    :items="visualizationMappings"
                    :fields="fields"
                    empty-text="No datatype visualization mappings defined."
                    class="mb-0">
                    <template v-slot:cell(actions)="row">
                        <BButton
                            size="sm"
                            variant="danger"
                            :disabled="isDeleting[row.item.datatype]"
                            @click="confirmDelete(row.item)">
                            <font-awesome-icon v-if="isDeleting[row.item.datatype]" icon="spinner" pulse />
                            <font-awesome-icon v-else icon="trash" />
                            Delete
                        </BButton>
                    </template>
                </BTable>
            </BCard>
        </div>

        <!-- Confirmation modal -->
        <BModal
            v-model="showDeleteModal"
            title="Confirm Deletion"
            ok-variant="danger"
            ok-title="Delete"
            @ok="deleteMapping">
            <p>
                Are you sure you want to delete the visualization mapping for datatype
                <strong>{{ selectedMapping?.datatype }}</strong
                >?
            </p>
        </BModal>
    </div>
</template>

<script setup lang="ts">
import {
    BAlert,
    BButton,
    BCard,
    BForm,
    BFormGroup,
    BFormSelect,
    BFormSelectOption,
    BModal,
    BTable,
} from "bootstrap-vue";
import { computed, onMounted, ref } from "vue";

import { type DatatypeVisualization } from "@/api/datatypeVisualizations";
import { fetchPlugins } from "@/api/plugins";
import { useDatatypeStore } from "@/stores/datatypeStore";
import { useDatatypeVisualizationsStore } from "@/stores/datatypeVisualizationsStore";

const datatypeVisualizationsStore = useDatatypeVisualizationsStore();
const datatypeStore = useDatatypeStore();

// State
const isLoading = ref(true);
const error = ref("");
const availableDatatypes = ref<Array<{ value: string; text: string }>>([]);
const availableVisualizations = ref<Array<{ value: string; text: string }>>([]);
const newMapping = ref<DatatypeVisualization>({
    datatype: "",
    visualization: "",
});
const showDeleteModal = ref(false);
const selectedMapping = ref<DatatypeVisualization | null>(null);
const isDeleting = ref<Record<string, boolean>>({});

// Table configuration
const fields = [
    { key: "datatype", label: "Datatype", sortable: true },
    { key: "visualization", label: "Visualization", sortable: true },
    { key: "actions", label: "Actions" },
];

// Computed properties
const visualizationMappings = computed(() => {
    return datatypeVisualizationsStore.visualizationMappings;
});

const isFormValid = computed(() => {
    return newMapping.value.datatype && newMapping.value.visualization;
});

// Initialize component
async function initialize() {
    isLoading.value = true;
    error.value = "";

    try {
        // Load datatypes
        await datatypeStore.loadDatatypes();

        // Convert to select options
        availableDatatypes.value = Object.entries(datatypeStore.datatypes)
            .map(([ext, info]) => ({
                value: ext,
                text: `${ext} - ${info.description || ext}`,
            }))
            .sort((a, b) => a.text.localeCompare(b.text));

        // Load visualizations
        const plugins = await fetchPlugins();
        availableVisualizations.value = plugins
            .map((plugin) => ({
                value: plugin.name,
                text: plugin.name,
            }))
            .sort((a, b) => a.text.localeCompare(b.text));

        // Load existing mappings
        await datatypeVisualizationsStore.loadAllMappings();
    } catch (e) {
        error.value = e instanceof Error ? e.message : String(e);
    } finally {
        isLoading.value = false;
    }
}

// Add a new mapping
async function addNewMapping() {
    if (!isFormValid.value) {
        return;
    }

    try {
        await datatypeVisualizationsStore.updateMapping(newMapping.value);

        // Reset form
        newMapping.value = {
            datatype: "",
            visualization: "",
        };
    } catch (e) {
        error.value = e instanceof Error ? e.message : String(e);
    }
}

// Confirm deletion of a mapping
function confirmDelete(mapping: DatatypeVisualization) {
    selectedMapping.value = mapping;
    showDeleteModal.value = true;
}

// Delete a mapping
async function deleteMapping() {
    if (!selectedMapping.value) {
        return;
    }

    const datatype = selectedMapping.value.datatype;
    isDeleting.value[datatype] = true;

    try {
        await datatypeVisualizationsStore.deleteMapping(datatype);
    } catch (e) {
        error.value = e instanceof Error ? e.message : String(e);
    } finally {
        isDeleting.value[datatype] = false;
        selectedMapping.value = null;
    }
}

// Load data when component is mounted
onMounted(initialize);
</script>

<style scoped>
.datatype-visualizations-manager {
    padding: 1rem;
}
</style>
