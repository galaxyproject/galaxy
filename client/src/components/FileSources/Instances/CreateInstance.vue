<script setup lang="ts">
import { computed, watch } from "vue";

import type { UserFileSourceModel } from "@/api/fileSources";
import { useFileSourceTemplatesStore } from "@/stores/fileSourceTemplatesStore";

import { useInstanceRouting } from "./routing";
import { getOAuth2Info } from "./services";

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
const template = computed(() => fileSourceTemplatesStore.getLatestTemplate(props.templateId));
const requiresOAuth2AuthorizeRedirect = computed(() => {
    const templateValue = template.value;
    return props.uuid == undefined && templateValue && OAUTH2_TYPES.indexOf(templateValue.type) >= 0;
});

async function onCreated(objectStore: UserFileSourceModel) {
    const message = `Created file source ${objectStore.name}`;
    goToIndex({ message });
}

watch(
    requiresOAuth2AuthorizeRedirect,
    async (requiresAuth) => {
        const templateValue = template.value;
        if (templateValue && requiresAuth) {
            const { data } = await getOAuth2Info({
                template_id: templateValue.id,
                template_version: templateValue.version || 0,
            });
            window.location.href = data.authorize_url;
        } else {
            console.log("skipping this...");
        }
    },
    { immediate: true }
);
</script>

<template>
    <div>
        <LoadingSpan v-if="!template" message="Loading file source templates" />
        <LoadingSpan
            v-else-if="requiresOAuth2AuthorizeRedirect"
            message="Fetching redirect information, you will need to authorize Galaxy to have access to this resource remotely" />
        <CreateForm v-else :uuid="uuid" :template="template" @created="onCreated"></CreateForm>
    </div>
</template>
