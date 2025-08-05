<script setup lang="ts">
import { useDebounce } from "@vueuse/core";
import { BButton, BFormCheckbox, BFormInput, BInputGroup, BInputGroupAppend } from "bootstrap-vue";
import { computed, ref } from "vue";

import { getFullAppUrl } from "@/app/utils";
import { copy } from "@/utils/clipboard";

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
    let url = getFullAppUrl(`published/page?id=${props.id}&embed=true`);
    url += `&heading=${settings.value.showHeading}`;
    return url;
});

const embedStyle = computed(() => {
    if (settings.value.applyStyle) {
        return ` width="${settings.value.width}px" height="${settings.value.height}px" style="border: 1px solid #ddd; border-radius: 4px;" `;
    }
    return " ";
});

const embed = computed(() => `<iframe title="Galaxy Page Embed"${embedStyle.value}src="${embedUrl.value}"></iframe>`);

const showEmbed = ref(false);
const showEmbedDebounced = useDebounce(showEmbed, 100);

const copied = ref(false);

function onCopy() {
    copy(embed.value);
    copied.value = true;
    setTimeout(() => {
        copied.value = false;
    }, 2000);
}
</script>

<template>
    <div class="page-embed">
        <div class="settings">
            <h4>Settings</h4>

            <BFormCheckbox v-model="settings.showHeading" switch> Show page title </BFormCheckbox>

            <BFormCheckbox v-model="settings.applyStyle" switch> Apply default styling </BFormCheckbox>

            <div v-if="settings.applyStyle" class="dimension-controls">
                <label>
                    Width
                    <BFormInput v-model.number="settings.width" type="number" min="200" max="2000" step="50" />
                </label>
                <label>
                    Height
                    <BFormInput v-model.number="settings.height" type="number" min="200" max="2000" step="50" />
                </label>
            </div>
        </div>

        <div class="preview">
            <label for="embed-code" class="w-100">
                Embed code
                <BInputGroup id="embed-code">
                    <BFormInput class="embed-code-input" :value="embed" readonly />
                    <BInputGroupAppend>
                        <BButton variant="primary" @click="onCopy">
                            {{ copied ? "Copied!" : "Copy" }}
                        </BButton>
                    </BInputGroupAppend>
                </BInputGroup>
            </label>

            <BFormCheckbox v-model="showEmbed" switch>Show embed Preview</BFormCheckbox>
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
@import "theme/blue.scss";

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

        .dimension-controls {
            display: flex;
            gap: 1rem;
            margin-top: 0.5rem;

            label {
                flex: 1;
                font-size: 0.875rem;
            }
        }
    }

    .preview {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 1rem;

        .embed-code-input {
            background-color: transparent;
            font-family: monospace;
            font-size: 0.875rem;
        }

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
