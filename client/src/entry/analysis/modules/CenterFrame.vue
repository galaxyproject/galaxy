<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import { withPrefix } from "@/utils/redirect";

import LoadingSpan from "@/components/LoadingSpan.vue";

const emit = defineEmits(["load"]);
const props = withDefaults(
    defineProps<{
        id?: string;
        src?: string;
        html?: string;
    }>(),
    {
        id: "frame",
        src: "",
        html: "",
    },
);

const iframeRef = ref<HTMLIFrameElement>();
const srcWithRoot = computed(() => withPrefix(props.src));
const isLoading = ref(true);

function injectHtml(val: string) {
    if (iframeRef.value && val) {
        iframeRef.value.srcdoc = val;
    }
}

function onLoad(ev: Event) {
    isLoading.value = false;
    const iframe = ev.currentTarget as HTMLIFrameElement;
    const location = iframe?.contentWindow && iframe.contentWindow.location;
    try {
        if (location && location.host && location.pathname != "/") {
            emit("load");
        }
    } catch (err) {
        console.warn("[CenterFrame] onLoad location access forbidden.", ev, location);
    }
}

watch(() => props.html, injectHtml);
onMounted(() => injectHtml(props.html));
</script>

<template>
    <div class="h-100">
        <LoadingSpan v-if="isLoading">Loading ...</LoadingSpan>
        <iframe
            :id="id"
            ref="iframeRef"
            :name="id"
            :src="props.html ? undefined : srcWithRoot"
            class="center-frame"
            frameborder="0"
            title="galaxy frame"
            width="100%"
            height="100%"
            @load="onLoad" />
    </div>
</template>
