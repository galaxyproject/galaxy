<script lang="ts" setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";

import SelectTemplate from "./SelectTemplate.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const loadingTemplatesInfoMessage = "Loading object store templates";

const objectStoreTemplatesStore = useObjectStoreTemplatesStore();
objectStoreTemplatesStore.ensureTemplates();

const templates = computed(() => objectStoreTemplatesStore.latestTemplates);
const loading = computed(() => objectStoreTemplatesStore.loading);

const router = useRouter();

const error = ref<string | null>(null);

async function chooseTemplate(selectTemplateId: string) {
    router.push({
        path: `/object_store_templates/${selectTemplateId}/new`,
    });
}
</script>
<template>
    <b-container fluid class="p-0">
        <LoadingSpan v-if="loading" :message="loadingTemplatesInfoMessage" />
        <div v-else>
            <b-alert v-if="error" variant="danger" class="object-store-selection-error" show>
                {{ error }}
            </b-alert>

            <SelectTemplate :templates="templates" @onSubmit="chooseTemplate" />
        </div>
    </b-container>
</template>
