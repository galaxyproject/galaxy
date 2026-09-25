<script setup lang="ts">
import { computedAsync } from "@vueuse/core";
import { BAlert, BImg } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { type PathDestination, useDatasetPathDestination } from "@/composables/datasetPathDestination";
import { getAppRoot } from "@/onload/loadConfig";
import { addSearchParams } from "@/utils/url";

interface Props {
    historyDatasetId: string;
    path?: string;
    allowSizeToggle?: boolean;
}

const { datasetPathDestination } = useDatasetPathDestination();

const props = withDefaults(defineProps<Props>(), {
    allowSizeToggle: false,
});

const pathDestination = computedAsync<PathDestination | null>(async () => {
    return await datasetPathDestination.value(props.historyDatasetId, props.path);
}, null);

const imageUrl = computed(() => {
    if (props.path === undefined || props.path === "undefined") {
        return `${getAppRoot()}dataset/display?dataset_id=${props.historyDatasetId}&as_image=true`;
    }
    const fileLink = pathDestination.value?.fileLink;
    return fileLink ? addSearchParams(fileLink, { as_image: "true" }) : undefined;
});

const isImage = computedAsync(async () => {
    if (!imageUrl.value) {
        return null;
    }
    const res = await fetch(imageUrl.value);
    const buff = await res.blob();
    return buff.type.startsWith("image/");
}, true);

const imageSize = ref<{ width?: number; height?: number }>({});
watch(imageUrl, () => {
    imageSize.value = {};
});

function onImageLoad(event: Event) {
    const img = event.target as HTMLImageElement;
    // SVGs with only a viewBox can collapse inside the inline-block wrapper.
    if (!img.width) {
        imageSize.value = { width: img.naturalWidth, height: img.naturalHeight };
    }
}

const isFluid = ref(true);

const toggleFluid = () => {
    isFluid.value = !isFluid.value;
};
</script>

<template>
    <div v-if="imageUrl" class="w-100">
        <BAlert v-if="!isImage" variant="warning" show>
            This dataset does not appear to be an image: {{ imageUrl }}.
        </BAlert>
        <div
            v-else
            class="image-wrapper"
            :class="{ interactive: props.allowSizeToggle }"
            @click="props.allowSizeToggle ? toggleFluid() : null">
            <BImg
                v-bind="imageSize"
                :key="imageUrl"
                :src="imageUrl"
                :fluid="isFluid"
                :class="{ 'cursor-pointer': props.allowSizeToggle }"
                @load="onImageLoad" />
            <div v-if="props.allowSizeToggle" class="size-hint">
                <small class="text-white">{{ isFluid ? "Click for actual size" : "Click to fit width" }}</small>
            </div>
        </div>
    </div>
    <BAlert v-else variant="warning" show>Image not found: {{ imageUrl }}.</BAlert>
</template>

<style lang="scss" scoped>
.image-wrapper {
    position: relative;
    display: inline-block;
}

.cursor-pointer {
    cursor: pointer;
    transition: transform 0.2s ease;
}

.interactive .cursor-pointer:hover {
    transform: scale(1.01);
}

.size-hint {
    position: absolute;
    bottom: 8px;
    right: 8px;
    background: rgba(0, 0, 0, 0.7);
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    opacity: 0;
    transition: opacity 0.2s ease;
    pointer-events: none;

    .image-wrapper:hover & {
        opacity: 1;
    }
}
</style>
