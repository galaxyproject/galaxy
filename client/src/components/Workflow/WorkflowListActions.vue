<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlus, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { useRouter } from "vue-router/composables";

library.add(faPlus, faUpload);

const router = useRouter();

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
    </div>
</template>
