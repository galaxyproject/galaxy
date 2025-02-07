<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useUserStore } from "@/stores/userStore";
import { withPrefix } from "@/utils/redirect";

import Alert from "@/components/Alert.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const emit = defineEmits(["load"]);
const props = withDefaults(
    defineProps<{
        id?: string;
        src?: string;
        isPreview?: boolean;
    }>(),
    {
        id: "frame",
        src: "",
        isPreview: false,
    }
);

const { isAdmin } = storeToRefs(useUserStore());
const srcWithRoot = computed(() => withPrefix(props.src));
const sanitizedImport = ref(false);
const sanitizedToolId = ref<String | false>(false);
const isLoading = ref(true);
watch(
    () => srcWithRoot.value,
    async () => {
        sanitizedImport.value = false;
        sanitizedToolId.value = false;
        if (props.isPreview) {
            try {
                const response = await fetch(srcWithRoot.value, { method: "HEAD" });
                const isImported = response.headers.get("x-sanitized-job-imported");
                const toolId = response.headers.get("x-sanitized-tool-id");
                if (isImported !== null) {
                    sanitizedImport.value = true;
                } else if (toolId !== null) {
                    sanitizedToolId.value = toolId;
                }
            } catch (e) {
                // I guess that's fine and the center panel will show something
                console.error(e);
            }
        }
    },
    { immediate: true }
);

const plainText = "Contents are shown as plain text.";
const sanitizedMessage = computed(() => {
    if (sanitizedImport.value) {
        return `Dataset has been imported. ${plainText}`;
    } else if (sanitizedToolId.value) {
        return `Dataset created by a tool that is not known to create safe HTML. ${plainText}`;
    }
    return undefined;
});

function onLoad(ev: Event) {
    isLoading.value = false;
    const iframe = ev.currentTarget as HTMLIFrameElement;
    const location = iframe?.contentWindow && iframe.contentWindow.location;
    try {
        if (location && location.host && location.pathname != "/") {
            emit("load");
        }
    } catch (err) {
        console.warn("CenterFrame - onLoad location access forbidden.", ev, location);
    }
}
</script>
<template>
    <div class="h-100">
        <Alert v-if="sanitizedMessage" :dismissible="true" variant="warning" data-description="sanitization warning">
            {{ sanitizedMessage }}
            <p v-if="isAdmin && sanitizedToolId">
                <router-link data-description="allowlist link" to="/admin/sanitize_allow">Review Allowlist</router-link>
                if outputs of {{ sanitizedToolId }} are trusted and should be shown as HTML.
            </p>
        </Alert>
        <LoadingSpan v-if="isLoading">Loading ...</LoadingSpan>
        <iframe
            :id="id"
            :name="id"
            :src="srcWithRoot"
            class="center-frame"
            frameborder="0"
            title="galaxy frame"
            width="100%"
            height="100%"
            @load="onLoad" />
    </div>
</template>
