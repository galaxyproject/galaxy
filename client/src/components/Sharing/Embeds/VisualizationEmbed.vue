<script setup lang="ts">
import { computed, ref } from "vue";

import { getFullAppUrl } from "@/app/utils";

import EmbedCode from "./EmbedCode.vue";
import EmbedSize from "./EmbedSize.vue";
import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";
import SavedVisualization from "@/components/Visualizations/SavedVisualization.vue";

const props = defineProps<{
    id: string;
}>();

const settings = ref({
    applyStyle: true,
    width: 800,
    height: 600,
});

const embedUrl = computed(() => getFullAppUrl(`widgets/visualizations/${props.id}`));

const embedStyle = computed(() => {
    if (settings.value.applyStyle) {
        return `width="${settings.value.width}" height="${settings.value.height}" style="border: none;"`;
    }
    return "";
});

const showEmbed = ref(false);
</script>

<template>
    <div class="visualization-embed">
        <div class="settings">
            <h4>Settings</h4>
            <GCheckbox v-model="settings.applyStyle" switch> Apply default styling </GCheckbox>
            <EmbedSize v-if="settings.applyStyle" v-model:width="settings.width" v-model:height="settings.height" />
        </div>

        <div class="preview">
            <EmbedCode title="Galaxy Visualization" :url="embedUrl" :attributes="embedStyle" />
            <GCheckbox v-model="showEmbed" class="align-self-start" switch>Show embed Preview</GCheckbox>
            <div v-if="showEmbed" class="visualization-preview">
                <SavedVisualization :visualization-id="props.id" embed />
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.visualization-embed {
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

        .visualization-preview {
            border: 2px solid $border-color;
            border-radius: 4px;
            height: 500px;
        }
    }
}

@media (max-width: 1200px) {
    .visualization-embed {
        flex-direction: column;

        .settings {
            min-width: unset;
        }
    }
}
</style>
