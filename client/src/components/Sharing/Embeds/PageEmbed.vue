<script setup lang="ts">
import { useDebounce } from "@vueuse/core";
import { BInputGroup, BInputGroupAppend } from "bootstrap-vue";
import { computed, ref } from "vue";

import { getFullAppUrl } from "@/app/utils";
import { EMBED_LABELS } from "@/components/Page/constants";
import { copy } from "@/utils/clipboard";

import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
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

// v-model casts a type="number" input's value to a number, but an empty or partial
// number ("-", "1e") comes through as ""; keep the last size then
function toSize(value: string | number | null, current: number) {
    if (typeof value === "number") {
        return value;
    }
    const size = parseFloat(value ?? "");
    return Number.isNaN(size) ? current : size;
}

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

const embed = computed(
    () => `<iframe title="${EMBED_LABELS.iframeTitle}"${embedStyle.value}src="${embedUrl.value}"></iframe>`,
);

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

            <!-- GCheckbox renders inline, so stack the switches here -->
            <div class="d-flex flex-column align-items-start">
                <GCheckbox v-model="settings.showHeading" switch> {{ EMBED_LABELS.showTitle }} </GCheckbox>

                <GCheckbox v-model="settings.applyStyle" switch> Apply default styling </GCheckbox>
            </div>

            <div v-if="settings.applyStyle" class="dimension-controls">
                <label>
                    Width
                    <GFormInput
                        :model-value="String(settings.width)"
                        type="number"
                        min="200"
                        max="2000"
                        step="50"
                        @update:model-value="settings.width = toSize($event, settings.width)" />
                </label>
                <label>
                    Height
                    <GFormInput
                        :model-value="String(settings.height)"
                        type="number"
                        min="200"
                        max="2000"
                        step="50"
                        @update:model-value="settings.height = toSize($event, settings.height)" />
                </label>
            </div>
        </div>

        <div class="preview">
            <label for="embed-code" class="w-100">
                Embed code
                <BInputGroup id="embed-code">
                    <GFormInput class="embed-code-input" :model-value="embed" readonly />
                    <BInputGroupAppend>
                        <GButton color="blue" @click="onCopy">
                            {{ copied ? "Copied!" : "Copy" }}
                        </GButton>
                    </BInputGroupAppend>
                </BInputGroup>
            </label>

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
