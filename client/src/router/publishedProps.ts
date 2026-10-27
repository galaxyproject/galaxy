import type { LocationQuery } from "vue-router";

import { parseBool } from "@/utils/utils";

export function pageProps(pageId: unknown, query: LocationQuery) {
    return {
        pageId,
        showHeading: query.heading ? parseBool(query.heading) : undefined,
    };
}

export function workflowProps(id: unknown, query: LocationQuery) {
    return {
        id,
        version: query.version,
        zoom: query.zoom ? parseFloat(query.zoom as string) : undefined,
        showButtons: query.buttons ? parseBool(query.buttons) : undefined,
        showAbout: query.about ? parseBool(query.about) : undefined,
        showHeading: query.heading ? parseBool(query.heading) : undefined,
        showMinimap: query.minimap ? parseBool(query.minimap) : undefined,
        showZoomControls: query.zoom_controls ? parseBool(query.zoom_controls) : undefined,
        initialX: query.initialX ? parseInt(query.initialX as string) : undefined,
        initialY: query.initialY ? parseInt(query.initialY as string) : undefined,
    };
}
