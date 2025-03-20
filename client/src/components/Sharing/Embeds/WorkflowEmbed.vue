<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCopy } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useDebounce } from "@vueuse/core";
import { BButton, BFormCheckbox, BFormInput, BInputGroup, BInputGroupAppend } from "bootstrap-vue";
import { computed, reactive, ref } from "vue";

import { copy } from "@/utils/clipboard";
import { getFullAppUrl } from "@/utils/utils";

import ZoomControl from "@/components/Workflow/Editor/ZoomControl.vue";
import WorkflowPublished from "@/components/Workflow/Published/WorkflowPublished.vue";

library.add(faCopy);

const props = defineProps<{
    id: string;
}>();

const settings = reactive({
    buttons: true,
    about: false,
    heading: false,
    minimap: true,
    zoomControls: true,
    initialX: -20,
    initialY: -20,
    zoom: 1,
    applyStyle: true,
});

function onChangePosition(event: Event, xy: "x" | "y") {
    const value = parseInt((event.target as HTMLInputElement).value);
    if (xy === "x") {
        settings.initialX = value;
    } else {
        settings.initialY = value;
    }
}

const embedUrl = computed(() => {
    let url = getFullAppUrl(`published/workflow?id=${props.id}&embed=true`);
    url += `&buttons=${settings.buttons}`;
    url += `&about=${settings.about}`;
    url += `&heading=${settings.heading}`;
    url += `&minimap=${settings.minimap}`;
    url += `&zoom_controls=${settings.zoomControls}`;
    url += `&initialX=${settings.initialX}&initialY=${settings.initialY}`;
    url += `&zoom=${settings.zoom}`;
    return url;
});

const embedStyle = computed(() => {
    if (settings.applyStyle) {
        return ' style="width: 100%; height: 700px; border: none;" ';
    } else {
        return " ";
    }
});
const embed = computed(
    () => `<iframe title="Galaxy Workflow Embed"${embedStyle.value}src="${embedUrl.value}"></iframe>`
);

// These Embed settings are not reactive, to we have to key them
const embedKey = computed(() => `zoom: ${settings.zoom}, x: ${settings.initialX}, y: ${settings.initialY}`);

const debouncedEmbedKey = useDebounce(embedKey, 500);

const showEmbed = ref(false);
const showEmbedDebounced = useDebounce(showEmbed, 100);

const copied = ref(false);

function onCopy() {
    copy(embed.value);
    copied.value = true;
}

function onCopyOut() {
    copied.value = false;
}

const clipboardTitle = computed(() => (copied.value ? "Copied!" : "Copy URL"));
</script>

<template>
    <div class="workflow-embed">
        <div class="settings">
            <BFormCheckbox v-model="settings.heading"> Show heading </BFormCheckbox>
            <BFormCheckbox v-model="settings.about"> Show about </BFormCheckbox>
            <BFormCheckbox v-model="settings.buttons"> Show buttons </BFormCheckbox>
            <BFormCheckbox v-model="settings.minimap"> Show minimap </BFormCheckbox>
            <BFormCheckbox v-model="settings.zoomControls"> Show zoom controls </BFormCheckbox>

            <label for="embed-position-control" class="control-label">
                Initial position
                <div id="embed-position-control" class="position-control">
                    <label>
                        x:
                        <input
                            :value="settings.initialX"
                            type="number"
                            @change="(event) => onChangePosition(event, 'x')" />
                    </label>

                    <label>
                        y:
                        <input
                            :value="settings.initialY"
                            type="number"
                            @change="(event) => onChangePosition(event, 'y')" />
                    </label>
                </div>
            </label>

            <label for="embed-zoom-control" class="control-label">
                Initial zoom
                <ZoomControl
                    id="embed-zoom-control"
                    :zoom-level="settings.zoom"
                    class="zoom-control"
                    @onZoom="(level) => (settings.zoom = level)" />
            </label>

            <BFormCheckbox
                v-model="settings.applyStyle"
                title="adds a width, height, and removes the border of the iframe">
                Add basic styling
            </BFormCheckbox>
        </div>
        <div class="preview">
            <label for="embed-code" class="w-100">
                Embed code
                <BInputGroup id="embed-code">
                    <BFormInput class="embed-code-input" :value="embed" readonly />
                    <BInputGroupAppend>
                        <BButton
                            v-b-tooltip.hover
                            :title="clipboardTitle"
                            variant="primary"
                            @click="onCopy"
                            @blur="onCopyOut">
                            <FontAwesomeIcon icon="copy" />
                        </BButton>
                    </BInputGroupAppend>
                </BInputGroup>
            </label>

            <BFormCheckbox v-model="showEmbed" switch>Show embed Preview</BFormCheckbox>
            <WorkflowPublished
                v-if="showEmbedDebounced"
                :id="props.id"
                :key="debouncedEmbedKey"
                class="published-preview"
                :zoom="settings.zoom"
                embed
                :show-about="settings.about"
                :show-buttons="settings.buttons"
                :show-heading="settings.heading"
                :show-minimap="settings.minimap"
                :show-zoom-controls="settings.zoomControls"
                :initial-x="settings.initialX"
                :initial-y="settings.initialY" />
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.workflow-embed {
    display: flex;
    gap: 0.5rem;
}

@container (max-width: 1200px) {
    .workflow-embed {
        flex-direction: column;
    }
}

.workflow-embed {
    .settings {
        flex: 1;
        display: flex;
        align-items: flex-start;
        justify-content: flex-start;
        flex-direction: column;
    }

    .preview {
        flex: 1;

        .published-preview {
            border: 2px solid $brand-primary;
            border-radius: 4px;
            width: 100%;
            height: 550px;
        }

        .embed-code-input {
            background-color: transparent;
        }
    }
}

.control-label {
    display: flex;
    flex-direction: column;
    margin-top: 0.25rem;
}

.zoom-control,
.position-control {
    position: unset;
    padding: 2px 4px;
    border-color: $brand-primary;
    border-radius: 4px;
    border-width: 1px;
    border-style: solid;
}

.position-control {
    display: flex;
    flex-direction: column;
    width: 9rem;

    input {
        width: 100%;
    }

    label {
        margin-bottom: 0;
        display: flex;
        gap: 0.25rem;
        align-items: center;
    }
}
</style>
