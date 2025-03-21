<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlus, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { useUserStore } from "@/stores/userStore";

library.add(faPlus, faUpload);

const router = useRouter();

const userStore = useUserStore();

const { isAnonymous } = storeToRefs(userStore);

const createButtonTitle = computed(() => {
    if (isAnonymous.value) {
        return "登录以创建工作流";
    } else {
        return "创建新工作流";
    }
});
const importButtonTitle = computed(() => {
    if (isAnonymous.value) {
        return "登录以导入工作流";
    } else {
        return "从URL或文件导入工作流";
    }
});

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
                v-b-tooltip.hover.noninteractive
                size="sm"
                :title="createButtonTitle"
                variant="outline-primary"
                :disabled="isAnonymous"
                @click="navigateToOldCreate">
                <FontAwesomeIcon :icon="faPlus" />
                创建
            </BButton>

            <BButton
                id="workflow-import"
                v-b-tooltip.hover.noninteractive
                size="sm"
                :title="importButtonTitle"
                variant="outline-primary"
                :disabled="isAnonymous"
                @click="navigateToImport">
                <FontAwesomeIcon :icon="faUpload" />
                导入
            </BButton>
        </div>
    </div>
</template>
