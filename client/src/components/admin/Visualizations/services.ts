/**
 * API service for admin visualization management
 */

import axios from "axios";

import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

export interface Visualization {
    id: string;
    package: string;
    version: string;
    enabled: boolean;
    installed: boolean;
    path?: string;
    size?: number;
    metadata?: {
        description?: string;
        author?: string;
        license?: string;
        dependencies?: Record<string, string>;
        homepage?: string;
    };
}

export interface AvailableVisualization {
    name: string;
    description: string;
    version: string;
    keywords: string[];
    modified: string;
    maintainers: Array<{
        username: string;
        email: string;
    }>;
    homepage?: string;
    repository?: string;
}

export interface InstallRequest {
    package: string;
    version: string;
}

export interface UsageStats {
    days: number;
    stats: Record<string, number>;
}

export interface StagingResult {
    message: string;
    staged_count: number;
    staged_visualizations: string[];
    errors?: string[];
}

export interface VisualizationStagingResult {
    message: string;
    visualization_id: string;
    source_path: string;
    target_path: string;
    size: number;
}

export interface CleanStagingResult {
    message: string;
    cleaned_count: number;
    cleaned_items: string[];
}

export interface StagingStatus {
    message: string;
    staged_count: number;
    staged_visualizations: Array<{
        name: string;
        path: string;
        size: number;
        last_modified: number;
    }>;
    total_size: number;
}

export async function getInstalledVisualizations(includeDisabled = true): Promise<Visualization[]> {
    const url = `${getAppRoot()}api/admin/visualizations`;
    const params = includeDisabled ? { include_disabled: true } : {};

    try {
        const response = await axios.get(url, { params });
        return response.data;
    } catch (error) {
        rethrowSimple(error);
        throw error;
    }
}

export async function getAvailableVisualizations(search?: string): Promise<AvailableVisualization[]> {
    const url = `${getAppRoot()}api/admin/visualizations/available`;
    const params = search ? { search } : {};

    try {
        const response = await axios.get(url, { params });
        return response.data;
    } catch (error) {
        rethrowSimple(error);
        throw error;
    }
}

export async function getVisualizationDetails(vizId: string): Promise<Visualization> {
    const url = `${getAppRoot()}api/admin/visualizations/${vizId}`;

    try {
        const response = await axios.get(url);
        return response.data;
    } catch (error) {
        rethrowSimple(error);
        throw error;
    }
}

export async function installVisualization(
    vizId: string,
    packageName: string,
    version: string
): Promise<Visualization> {
    const url = `${getAppRoot()}api/admin/visualizations/${vizId}/install`;

    try {
        const response = await axios.post(url, {
            package: packageName,
            version: version,
        });
        return response.data;
    } catch (error) {
        rethrowSimple(error);
        throw error;
    }
}

export async function updateVisualization(vizId: string, version: string): Promise<Visualization> {
    const url = `${getAppRoot()}api/admin/visualizations/${vizId}/update`;

    try {
        const response = await axios.put(url, { version });
        return response.data;
    } catch (error) {
        rethrowSimple(error);
        throw error;
    }
}

export async function uninstallVisualization(vizId: string): Promise<void> {
    const url = `${getAppRoot()}api/admin/visualizations/${vizId}`;

    try {
        await axios.delete(url);
    } catch (error) {
        rethrowSimple(error);
        throw error;
    }
}

export async function toggleVisualization(
    vizId: string,
    enabled: boolean
): Promise<{ id: string; enabled: boolean; message: string }> {
    const url = `${getAppRoot()}api/admin/visualizations/${vizId}/toggle`;

    try {
        const response = await axios.put(url, { enabled });
        return response.data;
    } catch (error) {
        rethrowSimple(error);
        throw error;
    }
}

export async function reloadVisualizationRegistry(): Promise<{ message: string }> {
    const url = `${getAppRoot()}api/admin/visualizations/reload`;

    try {
        const response = await axios.post(url);
        return response.data;
    } catch (error) {
        rethrowSimple(error);
        throw error;
    }
}

export async function getVisualizationUsageStats(days = 30): Promise<UsageStats> {
    const url = `${getAppRoot()}api/admin/visualizations/usage_stats`;
    const params = { days };

    try {
        const response = await axios.get(url, { params });
        return response.data;
    } catch (error) {
        rethrowSimple(error);
        throw error;
    }
}

// Staging operations
export async function stageAllVisualizations(): Promise<StagingResult> {
    const url = `${getAppRoot()}api/admin/visualizations/stage`;

    try {
        const response = await axios.post(url);
        return response.data;
    } catch (error) {
        rethrowSimple(error);
        throw error;
    }
}

export async function stageVisualization(vizId: string): Promise<VisualizationStagingResult> {
    const url = `${getAppRoot()}api/admin/visualizations/${vizId}/stage`;

    try {
        const response = await axios.post(url);
        return response.data;
    } catch (error) {
        rethrowSimple(error);
        throw error;
    }
}

export async function cleanStagedAssets(): Promise<CleanStagingResult> {
    const url = `${getAppRoot()}api/admin/visualizations/staged`;

    try {
        const response = await axios.delete(url);
        return response.data;
    } catch (error) {
        rethrowSimple(error);
        throw error;
    }
}

export async function getStagingStatus(): Promise<StagingStatus> {
    const url = `${getAppRoot()}api/admin/visualizations/staging_status`;

    try {
        const response = await axios.get(url);
        return response.data;
    } catch (error) {
        rethrowSimple(error);
        throw error;
    }
}
