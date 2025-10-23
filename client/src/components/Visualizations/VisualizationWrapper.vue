<script setup lang="ts">
import { faExpand, faWindowMaximize } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import { BAlert, BButton } from "bootstrap-vue";
import { debounce } from "lodash";
import { computed, onMounted, ref } from "vue";

import { getAppRoot } from "@/onload/loadConfig";

const DELAY = 300;

const props = withDefaults(
    defineProps<{
        config: object;
        name: string;
        title?: string;
        height?: number;
        fullHeight?: boolean;
    }>(),
    {
        fullHeight: false,
        height: 400,
    },
);

const emit = defineEmits(["change", "load"]);

const emitChange = debounce((newValue: string) => {
    emit("change", newValue);
}, DELAY);

const errorMessage = ref("");
const expand = ref(false);
const iframeRef = ref<HTMLIFrameElement | null>(null);

const iframeClass = computed(() =>
    props.fullHeight
        ? "visualization-wrapper full-height"
        : expand.value
          ? "visualization-popout-wrapper"
          : "visualization-wrapper",
);

const iframeStyle = computed(() =>
    props.fullHeight || expand.value ? {} : { maxHeight: `${props.height}px`, minHeight: `${props.height}px` },
);

async function render() {
    if (!props.name) {
        errorMessage.value = "Visualization name is required!";
        return;
    }
    try {
        const { data: plugin } = await axios.get(`${getAppRoot()}api/plugins/${props.name}`);
        const pluginPath = plugin.href;
        const dataIncoming = {
            root: window.location.origin + getAppRoot(),
            visualization_config: props.config,
            visualization_plugin: plugin,
            visualization_title: props.title,
        };

        const iframe = iframeRef.value;
        if (!iframe) {
            errorMessage.value = "Frame has been invalidated.";
            return;
        }

        const iframeDocument = iframe.contentDocument;
        if (!iframeDocument) {
            errorMessage.value = "Failed to access iframe document.";
            return;
        }

        const container = iframeDocument.createElement("div");
        container.id = "app";
        container.setAttribute("data-incoming", JSON.stringify(dataIncoming));
        iframeDocument.body.appendChild(container);

        if (plugin?.entry_point?.attr?.src) {
            const script = iframeDocument.createElement("script");
            script.type = "module";
            script.src = `${pluginPath}/${plugin.entry_point.attr.src}`;
            iframeDocument.body.appendChild(script);
        } else {
            const error = iframeDocument.createElement("div");
            error.innerHTML = `Unable to locate plugin module for: ${props.name}.`;
            iframeDocument.body.appendChild(error);
        }

        if (plugin?.entry_point?.attr?.css) {
            const link = iframeDocument.createElement("link");
            link.rel = "stylesheet";
            link.href = `${pluginPath}/${plugin.entry_point.attr.css}`;
            iframeDocument.head.appendChild(link);
        }

        iframe.contentWindow?.addEventListener("message", (event) => {
            if (event.data.from === "galaxy-visualization") {
                emitChange(event.data);
            }
        });

        emit("load");
        errorMessage.value = "";
    } catch (e) {
        errorMessage.value = `Visualization '${props.name}' not available: ${e}.`;
    }
}

onMounted(() => render());
</script>

<template>
    <div v-if="errorMessage">
        <BAlert variant="danger" show>{{ errorMessage }}</BAlert>
    </div>
    <div v-else class="position-relative h-100">
        <iframe
            id="galaxy_visualization"
            ref="iframeRef"
            :class="iframeClass"
            title="visualization"
            :style="iframeStyle">
        </iframe>
        <BButton
            v-if="!props.fullHeight"
            class="visualization-popout-expand"
            variant="link"
            size="sm"
            title="Maximize"
            @click="expand = !expand">
            <FontAwesomeIcon :icon="faExpand" />
        </BButton>
        <BButton
            v-if="!props.fullHeight && expand"
            class="visualization-popout-close"
            variant="link"
            size="sm"
            title="Minimize"
            @click="expand = !expand">
            <FontAwesomeIcon :icon="faWindowMaximize" />
        </BButton>
    </div>
</template>

<style lang="scss">
@import "theme/blue.scss";

.visualization-popout-close {
    left: 1rem;
    position: fixed;
    margin: 0.2rem;
    padding: 0 0.5rem;
    top: 1rem;
    z-index: 1001;
}
.visualization-popout-expand {
    left: 0;
    padding: 0 0.5rem;
    position: absolute;
    top: 0;
}
.visualization-popout-wrapper {
    background: $white;
    border: $border-default;
    border-radius: $border-radius-base;
    height: calc(100vh - 2rem);
    left: 1rem;
    padding-top: 1.5rem;
    position: fixed;
    top: 1rem;
    width: calc(100vw - 2rem);
    z-index: 1000;
}
.visualization-wrapper {
    border: none;
    width: 100%;
    padding-top: 1.5rem;
}
.full-height {
    height: 100%;
    padding-top: 0 !important;
}
</style>
