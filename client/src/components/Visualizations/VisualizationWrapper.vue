<script setup lang="ts">
import axios from "axios";
import { onMounted, ref } from "vue";

import { getAppRoot } from "@/onload/loadConfig";

interface Props {
    name: string;
    dataIncoming: object;
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

    // TODO: Add validation and error handling
    const pluginPath = `${getAppRoot()}static/plugins/visualizations/${props.name}/static/`;
    const pluginSrc = `${pluginPath}${plugin.entry_point.attr.src}`;
    const pluginCss = `${pluginPath}${plugin.entry_point.attr.css}`;

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
        container.setAttribute("data-incoming", JSON.stringify(props.dataIncoming));
        iframeDocument.body.appendChild(container);

        // Inject the script tag for the plugin
        const script = iframeDocument.createElement("script");
        script.type = "module";
        script.src = pluginSrc;
        iframeDocument.body.appendChild(script);

        // Add a CSS link to the iframe document
        const link = iframeDocument.createElement("link");
        link.rel = "stylesheet";
        link.href = pluginCss;
        iframeDocument.head.appendChild(link);
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
