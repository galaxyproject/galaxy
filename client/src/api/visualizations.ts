import { type components, GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

export type VisualizationSummary = components["schemas"]["VisualizationSummary"];

/** Attributes the visualizations index can be sorted by. */
export type VisualizationSortByLiteral = "create_time" | "title" | "update_time" | "username" | undefined;

export interface LoadVisualizationsOptions {
    /** Include visualizations owned by the current user. */
    showOwn?: boolean;
    /** Include visualizations shared with the current user. */
    showShared?: boolean;
    /** Include published visualizations. */
    showPublished?: boolean;
    /** A mix of free text and GitHub-style tags used to filter the index. */
    search?: string;
    sortBy?: VisualizationSortByLiteral;
    sortDesc?: boolean;
    limit?: number;
    offset?: number;
}

export interface LoadVisualizationsResult {
    data: VisualizationSummary[];
    totalMatches: number;
}

/**
 * Fetches visualization summaries from the visualizations index.
 *
 * The `showOwn`/`showShared`/`showPublished` triplet is always sent explicitly so
 * callers never accidentally leak items from a scope they did not ask for.
 */
export async function loadVisualizations(options: LoadVisualizationsOptions = {}): Promise<LoadVisualizationsResult> {
    const {
        showOwn = true,
        showShared = false,
        showPublished = false,
        search = "",
        sortBy = "update_time",
        sortDesc = true,
        limit = 24,
        offset = 0,
    } = options;

    const { response, data, error } = await GalaxyApi().GET("/api/visualizations", {
        params: {
            query: {
                limit,
                offset,
                search,
                sort_by: sortBy,
                sort_desc: sortDesc,
                show_own: showOwn,
                show_published: showPublished,
                show_shared: showShared,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    const totalMatches = parseInt(response.headers.get("total_matches") ?? "0", 10) || 0;

    return { data, totalMatches };
}
