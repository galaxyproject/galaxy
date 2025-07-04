<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import type { UserFileSourceModel } from "@/api/fileSources";
import { useFileSourceTemplatesStore } from "@/stores/fileSourceTemplatesStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { useInstanceRouting } from "./routing";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import CreateForm from "@/components/FileSources/Instances/CreateForm.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    templateId: string;
    uuid?: string;
}

const OAUTH2_TYPES = ["dropbox", "googledrive"];

const fileSourceTemplatesStore = useFileSourceTemplatesStore();
fileSourceTemplatesStore.fetchTemplates();

const { goToIndex } = useInstanceRouting();

const props = defineProps<Props>();

const breadcrumbItems = computed(() => [
    { title: "User Preferences", to: "/user" },
    { title: "My Repositories", to: "/file_source_instances/index" },
    { title: "Create New", to: "/file_source_instances/create" },
    { title: template.value?.name || "Option" },
]);

const loading = ref(false);
const errorMessage = ref("");

const template = computed(() => fileSourceTemplatesStore.getLatestTemplate(props.templateId));
const redirectMessage = computed(
    () =>
        `You will redirected to ${template.value?.name} to authorize Galaxy to access this resource remotely. Please wait`
);
const requiresOAuth2AuthorizeRedirect = computed(() => {
    const templateValue = template.value;
    return props.uuid == undefined && templateValue && OAUTH2_TYPES.indexOf(templateValue.type) >= 0;
});

function onCreated(objectStore: UserFileSourceModel) {
    const message = `Created file source ${objectStore.name}`;

    goToIndex({ message });
}

watch(
    requiresOAuth2AuthorizeRedirect,
    async (requiresAuth) => {
        const templateValue = template.value;

        if (templateValue && requiresAuth) {
            loading.value = true;

            const { data, error: testRequestError } = await GalaxyApi().GET(
                "/api/file_source_templates/{template_id}/{template_version}/oauth2",
                {
                    params: {
                        path: {
                            template_id: templateValue.id,
                            template_version: templateValue.version || 0,
                        },
                    },
                }
            );

            if (testRequestError) {
                errorMessage.value = errorMessageAsString(testRequestError, "Error getting OAuth2 URL");

                loading.value = false;
            } else {
                window.location.href = data.authorize_url;
            }
        }
    },
    { immediate: true }
);
</script>

<template>
    <div>
        <div class="d-flex">
            <BreadcrumbHeading :items="breadcrumbItems" />
        </div>

        <BAlert v-if="loading" show variant="info">
            <LoadingSpan v-if="!template" message="Loading file source templates" />
            <LoadingSpan v-else-if="requiresOAuth2AuthorizeRedirect && !errorMessage" :message="redirectMessage" />
        </BAlert>

        <BAlert v-if="errorMessage" show variant="danger">
            {{ errorMessage }}
        </BAlert>
        <CreateForm v-if="!loading && template" :uuid="uuid" :template="template" @created="onCreated" />
    </div>
</template>
