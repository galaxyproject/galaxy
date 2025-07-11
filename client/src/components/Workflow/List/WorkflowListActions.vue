<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlus, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { useRouter } from "vue-router/composables";
import localize from "@/utils/localization";

import { useUserStore } from "@/stores/userStore";

import GButton from "@/components/BaseComponents/GButton.vue";

library.add(faPlus, faUpload);

const router = useRouter();

const userStore = useUserStore();

const { isAnonymous } = storeToRefs(userStore);

function navigateToImport() {
    router.push("/workflows/import");
}

function navigateToOldCreate() {
    router.push("/workflows/edit");
}
</script>

<template>
    <div id="workflow-list-actions" class="d-flex align-items-center flex-gapx-1">
        <GButton
            id="workflow-create"
            size="small"
            outline
            tooltip
            tooltip-placement="bottom"
            color="blue"
            :title="localize('Create new workflow')"
            disabled-title="Log in to create workflow"
            :disabled="isAnonymous"
            @click="navigateToOldCreate">
            <FontAwesomeIcon :icon="faPlus" />
            <span v-localize>Create</span>
        </GButton>

        <GButton
            id="workflow-import"
            outline
            tooltip
            tooltip-placement="bottom"
            size="small"
            :title="localize('Import workflow from URL or file')"
            disabled-title="Log in to import workflow"
            color="blue"
            :disabled="isAnonymous"
            @click="navigateToImport">
            <FontAwesomeIcon :icon="faUpload" />
            <span v-localize>Import</span>
        </GButton>
    </div>
</template>
