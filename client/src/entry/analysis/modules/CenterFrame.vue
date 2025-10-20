<script setup lang="ts">
import { computed, ref } from "vue";

import { withPrefix } from "@/utils/redirect";

import LoadingSpan from "@/components/LoadingSpan.vue";

const emit = defineEmits(["load"]);
const props = withDefaults(
    defineProps<{
        id?: string;
        src?: string;
    }>(),
    {
        id: "frame",
        src: "",
    },
);

const srcWithRoot = computed(() => withPrefix(props.src));
const isLoading = ref(true);

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
</script>
<template>
    <div class="h-100">
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
