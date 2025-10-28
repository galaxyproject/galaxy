<script setup lang="ts">
import axios from "axios";
import { BAlert } from "bootstrap-vue";
import { debounce } from "lodash";
import { onMounted, ref } from "vue";

import { getAppRoot } from "@/onload/loadConfig";

const DELAY = 300;

const props = defineProps<{
    config: object;
    name: string;
    title?: string;
}>();

const emit = defineEmits(["change", "load"]);

const emitChange = debounce((newValue: string) => {
    emit("change", newValue);
}, DELAY);

const errorMessage = ref("");
const iframeRef = ref<HTMLIFrameElement | null>(null);

const blankPageUrl = `${getAppRoot()}static/blank.html`;

async function render() {
    if (props.name) {
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
            if (iframe) {
                if (iframe.contentDocument?.readyState !== "complete") {
                    await new Promise<HTMLIFrameElement>((resolve) => {
                        iframe.onload = () => resolve(iframe);
                    });
                }

                const iframeDocument = iframe.contentDocument;
                if (iframeDocument) {
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
                } else {
                    errorMessage.value = "Failed to access iframe document.";
                }
            } else {
                errorMessage.value = "Frame has been invalidated.";
            }
        } catch (e) {
            errorMessage.value = `Visualization '${props.name}' not available: ${e}.`;
        }
    } else {
        errorMessage.value = "Visualization name is required!";
    }
}

onMounted(() => render());
</script>

<template>
    <div v-if="errorMessage">
        <BAlert variant="danger" show>{{ errorMessage }}</BAlert>
    </div>
    <iframe
        v-else
        class="position-relative h-100 w-100 border-0"
        id="galaxy_visualization"
        ref="iframeRef"
        :src="blankPageUrl"
        title="visualization" />
</template>
