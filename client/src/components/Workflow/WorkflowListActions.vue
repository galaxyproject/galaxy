<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlus, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BModal } from "bootstrap-vue";
import { ref } from "vue";
import { useRouter } from "vue-router/composables";

import WorkflowCreate from "@/components/Workflow/WorkflowCreate.vue";

library.add(faPlus, faUpload);

const router = useRouter();

const showCreateModal = ref(false);

function navigateToImport() {
    router.push("/workflows/import");
}

function navigateToOldCreate() {
    router.push("/workflows/edit");
}
</script>

<template>
    <div id="workflow-list-actions" class="d-flex justify-content-between">
        <div>
            <BButton
                id="workflow-create"
                v-b-tooltip.hover
                size="sm"
                title="Create new workflow"
                variant="outline-primary"
                @click="navigateToOldCreate">
                <!-- @click="showCreateModal = !showCreateModal"> -->
                <FontAwesomeIcon :icon="faPlus" />
                Create
            </BButton>

            <BButton
                id="workflow-import"
                v-b-tooltip.hover
                size="sm"
                title="Import workflow from URL or file"
                variant="outline-primary"
                @click="navigateToImport">
                <FontAwesomeIcon :icon="faUpload" />
                Import
            </BButton>
        </div>

        <BModal v-model="showCreateModal" hide-footer centered>
            <template v-slot:modal-title>
                <h4 class="modal-title">Create new workflow</h4>
            </template>

            <WorkflowCreate modal-view />
        </BModal>
    </div>
</template>
