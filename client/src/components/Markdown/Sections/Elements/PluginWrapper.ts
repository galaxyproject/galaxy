import { getAppRoot } from "@/onload/loadConfig"

class PluginWrapper extends HTMLElement {
    constructor() {
        super();
    }

    connectedCallback() {
        const pluginName = this.getAttribute("plugin-name");
        const pluginData = this.getAttribute("plugin-data") || "";

        const pluginPath = `${getAppRoot()}static/plugins/visualizations/${pluginName}/static/dist/index`;
        const pluginSrc = `${pluginPath}.js`;
        const pluginCss = `${pluginPath}.css`;

        if (!pluginSrc) {
            console.error("Plugin source not provided!");
            return;
        }

        // Create and append the iframe
        const iframe = document.createElement("iframe");
        iframe.style.border = "none";
        iframe.style.width = "100%";
        iframe.style.height = this.getAttribute("height") || "100%";

        // Load content into the iframe once it's ready
        iframe.onload = () => {
            const iframeDocument = iframe.contentDocument;
            if (!iframeDocument) {
                console.error("Failed to access iframe document.");
                return;
            }

            // Create the container for the plugin
            const container = iframeDocument.createElement("div");
            container.id = "app";
            container.setAttribute("data-incoming", pluginData);
            iframeDocument.body.appendChild(container);

            // Inject the script tag for the plugin
            const script = iframeDocument.createElement("script");
            script.type = "module";
            script.src = pluginSrc;
            iframeDocument.body.appendChild(script);

            // Add a CSS link to the iframe document
            const link = iframeDocument.createElement('link');
            link.rel = 'stylesheet';
            link.href = pluginCss;
            iframeDocument.head.appendChild(link);
        };

        this.appendChild(iframe);
    }
}

// Register the custom element
customElements.define("plugin-wrapper", PluginWrapper);

export default PluginWrapper;
