<script setup lang="ts">
import axios from "axios";
import { BAlert } from "bootstrap-vue";
import { debounce } from "lodash";
import { onBeforeUnmount, onMounted, ref } from "vue";

import { getAppRoot } from "@/onload/loadConfig";

const DELAY = 300;

interface Props {
    name: string;
    config: object;
    title?: string;
    visualizationId?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "change", payload: Record<string, any>): void;
    (e: "saved", saved: boolean): void;
    (e: "load"): void;
}>();

const emitChange = debounce((newValue: Record<string, any>) => {
    emit("change", newValue);
}, DELAY);

const errorMessage = ref<string>("");
const iframeRef = ref<HTMLIFrameElement | null>(null);

function onFrameMessage(event: MessageEvent) {
    const message = event.data;
    if (message?.from !== "galaxy-visualization") {
        return;
    }
    // Saved state is reported as it happens, so a guard never runs against a stale answer.
    if (message.visualization_saved !== undefined) {
        emit("saved", message.visualization_saved);
    }
    // A change rebuilds persisted content from the config, so a message without one is not a change.
    if (message.visualization_config !== undefined) {
        emitChange(message);
    }
}

function onWindowMessage(event: MessageEvent) {
    if (event.source === iframeRef.value?.contentWindow) {
        onFrameMessage(event);
    }
}

async function render() {
    if (props.name) {
        try {
            const { data: plugin } = await axios.get(`${getAppRoot()}api/plugins/${props.name}`);
            const pluginPath = plugin.href;
            const dataIncoming = {
                root: window.location.origin + getAppRoot(),
                visualization_config: props.config,
                visualization_id: props.visualizationId,
                visualization_plugin: plugin,
                visualization_title: props.title,
            };

            const iframe = iframeRef.value;
            if (iframe) {
                const iframeDocument = iframe.contentDocument;
                if (iframeDocument) {
                    const container = iframeDocument.createElement("div");
                    container.id = "app";
                    container.setAttribute("data-incoming", JSON.stringify(dataIncoming));
                    iframeDocument.body.appendChild(container);

                    if (plugin?.entry_point?.attr?.src) {
                        const script = iframeDocument.createElement("script");
                        script.type = plugin.entry_point.attr.type || "module";
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

                    iframe.contentWindow?.addEventListener("message", onFrameMessage);

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

onMounted(() => {
    window.addEventListener("message", onWindowMessage);
    render();
});

onBeforeUnmount(() => {
    window.removeEventListener("message", onWindowMessage);
    iframeRef.value?.contentWindow?.removeEventListener("message", onFrameMessage);
    emitChange.cancel();
});
</script>

<template>
    <div v-if="errorMessage">
        <BAlert variant="danger" show>{{ errorMessage }}</BAlert>
    </div>
    <iframe
        v-else
        id="galaxy_visualization"
        ref="iframeRef"
        class="position-relative h-100 w-100 border-0"
        title="visualization" />
</template>
