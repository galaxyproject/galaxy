/**
 * API service for admin visualization management
 */

import { type components, GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

export type Visualization = components["schemas"]["InstalledVisualizationResponse"];
export type AvailableVisualization = components["schemas"]["AvailableVisualizationResponse"];
export type StagingResult = components["schemas"]["StagingResultResponse"];
export type VisualizationStagingResult = components["schemas"]["VisualizationStagingResultResponse"];
export type CleanStagingResult = components["schemas"]["CleanStagingResultResponse"];
export type StagingStatus = components["schemas"]["StagingStatusResponse"];
export type UsageStats = components["schemas"]["UsageStatsResponse"];

export async function getInstalledVisualizations(includeDisabled = true) {
    const { data, error } = await GalaxyApi().GET("/api/admin/visualizations", {
        params: { query: { include_disabled: includeDisabled } },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}

export async function getAvailableVisualizations(search?: string) {
    const { data, error } = await GalaxyApi().GET("/api/admin/visualizations/available", {
        params: { query: { search: search ?? null } },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}

export async function getPackageVersions(packageName: string) {
    const { data, error } = await GalaxyApi().GET("/api/admin/visualizations/versions/{package_name}", {
        params: { path: { package_name: packageName } },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}

export async function installVisualization(vizId: string, packageName: string, version: string) {
    const { data, error } = await GalaxyApi().POST("/api/admin/visualizations/{viz_id}/install", {
        params: { path: { viz_id: vizId } },
        body: { package: packageName, version },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}

export async function updateVisualization(vizId: string, version: string) {
    const { data, error } = await GalaxyApi().PUT("/api/admin/visualizations/{viz_id}/update", {
        params: { path: { viz_id: vizId } },
        body: { version },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}

export async function uninstallVisualization(vizId: string) {
    const { error } = await GalaxyApi().DELETE("/api/admin/visualizations/{viz_id}", {
        params: { path: { viz_id: vizId } },
    });

    if (error) {
        rethrowSimple(error);
    }
}

export async function toggleVisualization(vizId: string, enabled: boolean) {
    const { data, error } = await GalaxyApi().PUT("/api/admin/visualizations/{viz_id}/toggle", {
        params: { path: { viz_id: vizId } },
        body: { enabled },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}

export async function reloadVisualizationRegistry() {
    const { data, error } = await GalaxyApi().POST("/api/admin/visualizations/reload");

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}

export async function getVisualizationUsageStats(days = 30) {
    const { data, error } = await GalaxyApi().GET("/api/admin/visualizations/usage_stats", {
        params: { query: { days } },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}

export async function stageAllVisualizations() {
    const { data, error } = await GalaxyApi().POST("/api/admin/visualizations/stage");

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}

export async function stageVisualization(vizId: string) {
    const { data, error } = await GalaxyApi().POST("/api/admin/visualizations/{viz_id}/stage", {
        params: { path: { viz_id: vizId } },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}

export async function cleanStagedAssets() {
    const { data, error } = await GalaxyApi().DELETE("/api/admin/visualizations/staged");

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}

export async function getStagingStatus() {
    const { data, error } = await GalaxyApi().GET("/api/admin/visualizations/staging_status");

    if (error) {
        rethrowSimple(error);
    }

    return data!;
}
