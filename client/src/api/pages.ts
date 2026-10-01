/**
 * Unified API client for all Galaxy Pages (history-attached and standalone).
 * Uses the generated typed client against the /api/pages endpoints.
 */
import { type components, GalaxyApi, type GalaxyApiPaths } from "@/api";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";
import { slugify } from "@/utils/slug";

// --- Types (generated from the backend Page/PageRevision schemas) ---

export type HistoryPageSummary = components["schemas"]["PageSummary"];
export type HistoryPageDetails = components["schemas"]["PageDetails"];
export type PageRevisionSummary = components["schemas"]["PageRevisionSummary"];
export type PageRevisionDetails = components["schemas"]["PageRevisionDetails"];
export type CreateHistoryPagePayload = components["schemas"]["CreatePagePayload"];
export type UpdateHistoryPagePayload = components["schemas"]["UpdatePagePayload"];

/** Neutral aliases for pages which are not necessarily attached to a history. */
export type PageSummary = HistoryPageSummary;
export type PageDetails = HistoryPageDetails;
export type PageContentFormat = components["schemas"]["PageContentFormat"];

export type PageSortBy = NonNullable<
    NonNullable<GalaxyApiPaths["/api/pages"]["get"]["parameters"]["query"]>["sort_by"]
>;

export interface LoadPagesOptions {
    /** Include pages owned by the current user. */
    showOwn?: boolean;
    /** Include pages shared with the current user. */
    showShared?: boolean;
    /** Include published pages. */
    showPublished?: boolean;
    /** Free text and GitHub-style tag filters. */
    search?: string;
    sortBy?: PageSortBy;
    sortDesc?: boolean;
    limit?: number;
    offset?: number;
}

export interface LoadPagesResult {
    data: PageSummary[];
    totalMatches: number;
}

export interface CreatePageOptions {
    title: string;
    slug: string;
    /** Defaults to `markdown` (the format used by the page editor). */
    content_format?: PageContentFormat;
    content?: string;
}

// --- API functions ---

/**
 * Pages that are not attached to a history have their type set to "standalone" on the backend,
 * so the user facing `is:standalone` filter is converted before being sent to the backend.
 */
function normalizePageSearch(search: string): string {
    return search.includes("is:standalone") ? search.replace("is:standalone", "type:standalone") : search;
}

/** Lists pages visible to the current user, optionally restricted to own/shared/published ones. */
export async function loadPages(options: LoadPagesOptions = {}): Promise<LoadPagesResult> {
    const {
        showOwn = true,
        showShared = false,
        showPublished = false,
        search = "",
        sortBy = "update_time",
        sortDesc = true,
        limit = 20,
        offset = 0,
    } = options;

    const { response, data, error } = await GalaxyApi().GET("/api/pages", {
        params: {
            query: {
                limit,
                offset,
                search: normalizePageSearch(search),
                sort_by: sortBy,
                sort_desc: sortDesc,
                show_own: showOwn,
                show_shared: showShared,
                show_published: showPublished,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    const totalMatches = parseInt(response.headers.get("total_matches") ?? "0", 10) || 0;

    return { data, totalMatches };
}

/** Backend `err_code` of a slug the user already owns (`USER_SLUG_DUPLICATE`) */
const USER_SLUG_DUPLICATE = 400006;

/** Thrown by {@link createPage} when the user already owns a page with that slug */
export class PageSlugConflictError extends Error {
    constructor(message: string) {
        super(message);
        this.name = "PageSlugConflictError";
    }
}

/** Creates a standalone page and returns the created page. */
export async function createPage({
    title,
    slug,
    content_format = "markdown",
    content = "",
}: CreatePageOptions): Promise<PageDetails> {
    const { data, error } = await GalaxyApi().POST("/api/pages", { body: { title, slug, content, content_format } });
    if (error) {
        if (error.err_code === USER_SLUG_DUPLICATE) {
            throw new PageSlugConflictError(errorMessageAsString(error));
        }
        rethrowSimple(error);
    }
    return data;
}

/** Creates a page slugged from its title; a slug the user already owns is retried once with `-2` */
export async function createPageFromTitle(options: Omit<CreatePageOptions, "slug">): Promise<PageDetails> {
    // a title made of punctuation alone would leave no slug to send
    const slug = slugify(options.title, "page");
    try {
        return await createPage({ ...options, slug });
    } catch (error) {
        if (!(error instanceof PageSlugConflictError)) {
            throw error;
        }
        // the suffixed slug is free unless the user owns both, which is worth reporting
        return createPage({ ...options, slug: `${slug}-2` });
    }
}

export async function fetchHistoryPages(historyId: string, invocationId?: string): Promise<HistoryPageSummary[]> {
    const { data, error } = await GalaxyApi().GET("/api/pages", {
        params: {
            query: {
                history_id: historyId,
                invocation_id: invocationId,
                show_own: true,
                show_published: false,
                sort_desc: true,
            },
        },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function fetchHistoryPage(pageId: string): Promise<HistoryPageDetails> {
    const { data, error } = await GalaxyApi().GET("/api/pages/{id}", {
        params: { path: { id: pageId } },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function createHistoryPage(payload: CreateHistoryPagePayload): Promise<HistoryPageDetails> {
    const { data, error } = await GalaxyApi().POST("/api/pages", { body: payload });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function updateHistoryPage(
    pageId: string,
    payload: UpdateHistoryPagePayload,
): Promise<HistoryPageDetails> {
    const { data, error } = await GalaxyApi().PUT("/api/pages/{id}", {
        params: { path: { id: pageId } },
        body: payload,
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

/** Save page content via PUT (replaces legacy POST /revisions save). */
export async function savePage(
    pageId: string,
    content: string,
    editSource: string = "user",
): Promise<HistoryPageDetails> {
    return updateHistoryPage(pageId, { content, edit_source: editSource });
}

export async function deleteHistoryPage(pageId: string): Promise<void> {
    const { error } = await GalaxyApi().DELETE("/api/pages/{id}", {
        params: { path: { id: pageId } },
    });
    if (error) {
        rethrowSimple(error);
    }
}

export async function fetchPageRevisions(
    pageId: string,
    { sortDesc = false }: { sortDesc?: boolean } = {},
): Promise<PageRevisionSummary[]> {
    const { data, error } = await GalaxyApi().GET("/api/pages/{id}/revisions", {
        params: { path: { id: pageId }, query: { sort_desc: sortDesc } },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function fetchPageRevision(pageId: string, revisionId: string): Promise<PageRevisionDetails> {
    const { data, error } = await GalaxyApi().GET("/api/pages/{id}/revisions/{revision_id}", {
        params: { path: { id: pageId, revision_id: revisionId } },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function revertPageRevision(pageId: string, revisionId: string): Promise<PageRevisionDetails> {
    const { data, error } = await GalaxyApi().POST("/api/pages/{id}/revisions/{revision_id}/revert", {
        params: { path: { id: pageId, revision_id: revisionId } },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}
