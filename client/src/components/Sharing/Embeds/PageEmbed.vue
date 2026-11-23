<script setup lang="ts">
import { useDebounce } from "@vueuse/core";
import { computed, ref } from "vue";

import { getFullAppUrl } from "@/app/utils";
import { EMBED_LABELS } from "@/components/Page/constants";

import EmbedCode from "./EmbedCode.vue";
import EmbedSize from "./EmbedSize.vue";
import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";
import PageView from "@/components/Page/PageView.vue";

interface Props {
    id: string;
}

const props = defineProps<Props>();

const settings = ref({
    showHeading: true,
    applyStyle: true,
    width: 800,
    height: 600,
});

const embedUrl = computed(() => {
    let url = getFullAppUrl(`widgets/pages/${props.id}`);
    url += `?heading=${settings.value.showHeading}`;
    return url;
});

const embedStyle = computed(() => {
    if (settings.value.applyStyle) {
        return `width="${settings.value.width}px" height="${settings.value.height}px" style="border: 1px solid #ddd; border-radius: 4px;"`;
    }
    return "";
});

const showEmbed = ref(false);
const showEmbedDebounced = useDebounce(showEmbed, 100);
</script>

<template>
    <div class="page-embed">
        <div class="settings">
            <h4>Settings</h4>

            <!-- GCheckbox renders inline, so stack the switches here -->
            <div class="d-flex flex-column align-items-start">
                <GCheckbox v-model="settings.showHeading" switch> {{ EMBED_LABELS.showTitle }} </GCheckbox>

                <GCheckbox v-model="settings.applyStyle" switch> Apply default styling </GCheckbox>
            </div>

            <EmbedSize v-if="settings.applyStyle" v-model:width="settings.width" v-model:height="settings.height" />
        </div>

        <div class="preview">
            <EmbedCode :title="EMBED_LABELS.iframeTitle" :url="embedUrl" :attributes="embedStyle" />

            <GCheckbox v-model="showEmbed" class="align-self-start" switch>Show embed Preview</GCheckbox>
            <PageView
                v-if="showEmbedDebounced"
                :page-id="props.id"
                class="page-preview"
                embed
                :show-heading="settings.showHeading" />
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.page-embed {
    display: flex;
    gap: 2rem;

    .settings {
        padding: 1rem;
        background-color: $brand-light;
        border-radius: 0.5rem;
        min-width: 250px;

        h4 {
            margin-bottom: 1rem;
        }
    }

    .preview {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 1rem;

        .page-preview {
            border: 2px solid $border-color;
            border-radius: 4px;
            overflow: hidden;
            height: 500px;
            min-height: 300px;
            padding: 0.5rem;
        }
    }
}

@media (max-width: 1200px) {
    .page-embed {
        flex-direction: column;

        .settings {
            min-width: unset;
        }
    }
}
</style>
