<script lang="ts" setup>
import { computed } from "vue";
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

async function chooseTemplate(selectTemplateId: string) {
    router.push({
        path: `/file_source_templates/${selectTemplateId}/new`,
    });
}
</script>
<template>
    <CreateInstance :loading-message="loadingTemplatesInfoMessage" :loading="loading" prefix="file-source">
        <SelectTemplate :templates="templates" @onSubmit="chooseTemplate" />
    </CreateInstance>
</template>
