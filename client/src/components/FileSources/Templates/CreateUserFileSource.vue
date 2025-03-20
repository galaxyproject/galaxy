<script lang="ts" setup>
import { BAlert } from "bootstrap-vue";
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useFileSourceTemplatesStore } from "@/stores/fileSourceTemplatesStore";

import SelectTemplate from "./SelectTemplate.vue";
import CreateInstance from "@/components/ConfigTemplates/CreateInstance.vue";

const loadingTemplatesInfoMessage = "Loading file source templates";

const fileSourceTemplatesStore = useFileSourceTemplatesStore();
fileSourceTemplatesStore.ensureTemplates();

const templates = computed(() => fileSourceTemplatesStore.latestTemplates);
const loading = computed(() => fileSourceTemplatesStore.loading);

const router = useRouter();

const errorMessage = ref("");

function chooseTemplate(selectTemplateId: string) {
    router.push({
        path: `/file_source_templates/${selectTemplateId}/new`,
    });
}

function handleOAuth2Redirect() {
    if (router.currentRoute.query.error === "access_denied") {
        errorMessage.value = "You must authorize Galaxy to access this resource. Please try again.";
    } else if (router.currentRoute.query.error) {
        const error = router.currentRoute.query.error;

        if (Array.isArray(error)) {
            errorMessage.value = error[0] || "There was an error creating the file source.";
        } else {
            errorMessage.value = error;
        }
    }
}

handleOAuth2Redirect();
</script>

<template>
    <CreateInstance :loading-message="loadingTemplatesInfoMessage" :loading="loading" prefix="file-source">
        <BAlert v-if="errorMessage" variant="danger" show dismissible>
            {{ errorMessage }}
        </BAlert>

        <SelectTemplate :templates="templates" @onSubmit="chooseTemplate" />
    </CreateInstance>
</template>
