<script setup lang="ts">
import axios from "axios";
import { BAlert } from "bootstrap-vue";
import { debounce } from "lodash";
import { onMounted, ref } from "vue";

import { getAppRoot } from "@/onload/loadConfig";

const DELAY = 300;

const props = defineProps<{
    config: Object;
    name: String;
    title: String;
}>();

const emit = defineEmits(["change"]);

const emitChange = debounce((newValue: string) => {
    emit("change", newValue);
}, DELAY);

const errorMessage = ref("");
const iframeRef = ref<HTMLIFrameElement | null>(null);

async function render() {
    if (!props.name) {
        errorMessage.value = "Visualization name is required!";
    } else {
        try {
            const { data: plugin } = await axios.get(`${getAppRoot()}api/plugins/${props.name}`);
            const pluginPath = `${getAppRoot()}static/plugins/visualizations/${props.name}/static/`;
            const dataIncoming = {
                root: window.location.origin + getAppRoot(),
                visualization_config: props.config,
                visualization_plugin: plugin,
                visualization_title: props.title,
            };

            const iframe = iframeRef.value;
            if (iframe) {
                // Verify document existence
                const iframeDocument = iframe.contentDocument;
                if (!iframeDocument) {
                    errorMessage.value = "Failed to access iframe document.";
                    return;
                }

                // Create the container for the plugin
                const container = iframeDocument.createElement("div");
                container.id = "app";
                container.setAttribute("data-incoming", JSON.stringify(dataIncoming));
                iframeDocument.body.appendChild(container);

                // Inject the script tag for the plugin
                if (plugin?.entry_point?.attr?.src) {
                    const script = iframeDocument.createElement("script");
                    script.type = "module";
                    script.src = `${pluginPath}${plugin.entry_point.attr.src}`;
                    iframeDocument.body.appendChild(script);
                } else {
                    const error = iframeDocument.createElement("div");
                    error.innerHTML = `Unable to locate plugin module for: ${props.name}.`;
                    iframeDocument.body.appendChild(error);
                }

                // Add a CSS link to the iframe document
                if (plugin?.entry_point?.attr?.css) {
                    const link = iframeDocument.createElement("link");
                    link.rel = "stylesheet";
                    link.href = `${pluginPath}${plugin.entry_point.attr.css}`;
                    iframeDocument.head.appendChild(link);
                }

                // Add event listener
                iframe.contentWindow?.addEventListener("message", (event) => {
                    if (event.data.from === "galaxy-visualization") {
                        emitChange(event.data);
                    }
                });

                // Reset error message
                errorMessage.value = "";
            } else {
                errorMessage.value = "Frame has been invalidated.";
            }
        } catch (e) {
            errorMessage.value = `Visualization '${props.name}' not available: ${e}.`;
        }
    }
}

onMounted(() => render());
</script>

<template>
    <div v-if="errorMessage">
        <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
    </div>
    <iframe v-else ref="iframeRef" title="visualization" class="visualization-wrapper"></iframe>
</template>

<style>
.visualization-wrapper {
    border: none;
    width: 100%;
}
</style>
