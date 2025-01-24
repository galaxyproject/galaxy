<script lang="ts" setup>
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";

import SelectTemplate from "./SelectTemplate.vue";
import CreateInstance from "@/components/ConfigTemplates/CreateInstance.vue";

const loadingTemplatesInfoMessage = "Loading storage location templates";

const objectStoreTemplatesStore = useObjectStoreTemplatesStore();
objectStoreTemplatesStore.ensureTemplates();

const templates = computed(() => objectStoreTemplatesStore.latestTemplates);
const loading = computed(() => objectStoreTemplatesStore.loading);

const router = useRouter();

async function chooseTemplate(selectTemplateId: string) {
    router.push({
        path: `/object_store_templates/${selectTemplateId}/new`,
    });
}
</script>
<template>
    <CreateInstance :loading-message="loadingTemplatesInfoMessage" :loading="loading" prefix="object-store">
        <SelectTemplate :templates="templates" @onSubmit="chooseTemplate" />
    </CreateInstance>
</template>
