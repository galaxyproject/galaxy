/**
 * API service for admin visualization management
 */

import { type components, GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

export type Visualization = components["schemas"]["InstalledVisualizationResponse"];
export type AvailableVisualization = components["schemas"]["AvailableVisualizationResponse"];

export async function getInstalledVisualizations(includeDisabled = true) {
    const { data, error } = await GalaxyApi().GET("/api/admin/plugins", {
        params: { query: { include_disabled: includeDisabled } },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}

export async function getAvailableVisualizations(search?: string) {
    const { data, error } = await GalaxyApi().GET("/api/admin/plugins/available", {
        params: { query: { search: search ?? null } },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}

export async function getPackageVersions(packageName: string) {
    const { data, error } = await GalaxyApi().GET("/api/admin/plugins/versions/{package_name}", {
        params: { path: { package_name: packageName } },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}

export async function installVisualization(packageName: string, version: string) {
    const { data, error } = await GalaxyApi().POST("/api/admin/plugins", {
        body: { package: packageName, version },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}

export async function updateVisualization(vizId: string, version: string) {
    const { data, error } = await GalaxyApi().PUT("/api/admin/plugins/{viz_id}/update", {
        params: { path: { viz_id: vizId } },
        body: { version },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}

export async function uninstallVisualization(vizId: string) {
    const { error } = await GalaxyApi().DELETE("/api/admin/plugins/{viz_id}", {
        params: { path: { viz_id: vizId } },
    });

    if (error) {
        rethrowSimple(error);
    }
}

export async function toggleVisualization(vizId: string, enabled: boolean) {
    const { data, error } = await GalaxyApi().PUT("/api/admin/plugins/{viz_id}/toggle", {
        params: { path: { viz_id: vizId } },
        body: { enabled },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}

export async function reloadVisualizationRegistry() {
    const { data, error } = await GalaxyApi().POST("/api/admin/plugins/reload");

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}
