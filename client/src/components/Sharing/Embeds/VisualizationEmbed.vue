<script setup lang="ts">
import { computed, ref } from "vue";

import { getFullAppUrl } from "@/app/utils";

import EmbedCode from "./EmbedCode.vue";
import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";
import SavedVisualization from "@/components/Visualizations/SavedVisualization.vue";

const props = defineProps<{
    id: string;
}>();

const embedUrl = computed(() => getFullAppUrl(`widgets/visualizations/${props.id}`));
const embedStyle = ' style="width: 100%; height: 600px; border: none;" ';

const showEmbed = ref(false);
</script>

<template>
    <div class="visualization-embed">
        <EmbedCode title="Galaxy Visualization" :url="embedUrl" :attributes="embedStyle" />
        <GCheckbox v-model="showEmbed" switch>Show embed Preview</GCheckbox>
        <div v-if="showEmbed" class="visualization-preview">
            <SavedVisualization :visualization-id="props.id" />
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.visualization-embed {
    display: flex;
    flex-direction: column;
    gap: 1rem;

    .visualization-preview {
        border: 2px solid $border-color;
        border-radius: 4px;
        height: 500px;
    }
}
</style>
