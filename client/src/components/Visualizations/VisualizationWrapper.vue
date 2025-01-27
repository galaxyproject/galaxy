<script setup lang="ts">
import axios from "axios";
import { onMounted, ref } from "vue";

import { getAppRoot } from "@/onload/loadConfig";

interface Props {
    name: string;
    config: object;
    height?: string;
}

const props = defineProps<Props>();

const iframeRef = ref<HTMLIFrameElement | null>(null);

onMounted(async () => {
    if (!props.name) {
        console.error("Plugin name is required!");
        return;
    }

    const { data: plugin } = await axios.get(`${getAppRoot()}api/plugins/${props.name}`);
    const pluginPath = `${getAppRoot()}static/plugins/visualizations/${props.name}/static/`;
    const dataIncoming = {
        root: getAppRoot(),
        visualization_plugin: plugin,
        visualization_config: props.config,
    };
    const iframe = iframeRef.value;
    if (iframe) {
        // Verify document existence
        const iframeDocument = iframe.contentDocument;
        if (!iframeDocument) {
            console.error("Failed to access iframe document.");
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
    }
});
</script>

<template>
    <iframe
        ref="iframeRef"
        title="visualization"
        class="visualization-wrapper"
        :style="{ height: props.height || '100%' }">
    </iframe>
</template>

<style>
.visualization-wrapper {
    border: none;
    width: 100%;
}
</style>
