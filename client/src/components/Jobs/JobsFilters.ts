import { JOB_STATES, type JobBaseModel, type JobsQueryParams, type JobState } from "@/api/jobs";
import { useToolStore } from "@/stores/toolStore";
import Filtering, { compare, contains, equals, toDate, type ValidFilter } from "@/utils/filtering";

/** Name mode sends every matching tool id in the query string, so keep the URL bounded. */
export const MAX_TOOL_NAME_MATCHES = 50;

export type JobTimeRangeKey = "30m" | "1h" | "24h" | "7d" | "custom";

/**
 * A curated, quick-toggle grouping of job states (see `JobStatusFilter.vue`).
 *
 * Each job state belongs to exactly one group. Named so a group key never collides with an actual
 * job state value (e.g. not `running`, which is itself a state).
 */
export const STATE_GROUPS: Record<string, JobState[]> = {
    active: ["new", "queued", "running", "finishing", "waiting", "resubmitted", "upload"],
    finished: ["ok", "skipped"],
    problem: ["error", "failed"],
    inactive: ["paused", "stop", "stopped", "deleting", "deleted"],
};

type UserJobsQueryParams = Pick<
    NonNullable<JobsQueryParams>,
    "state" | "date_range_min" | "date_range_max" | "search" | "tool_id"
>;

/** Base filters for the jobs list. */
const baseFilters: Record<string, ValidFilter<string | number>> = {
    state: {
        placeholder: "state",
        type: "Dropdown",
        handler: equals("state"),
        datalist: [...JOB_STATES],
        menuItem: true,
        disablesFilters: { status: null },
    },

    // Set only by the quick-toggle buttons (`JobStatusFilter.vue`), never shown as its own menu
    // field; see `STATE_GROUPS`.
    status: {
        type: "Dropdown",
        handler: equals("status"),
        datalist: Object.keys(STATE_GROUPS),
        menuItem: false,
    },

    update_time: {
        placeholder: "updated time",
        type: Date,
        handler: compare("update_time", "le", toDate),
        isRangeInput: true,
        menuItem: true,
    },
};

/** Valid filters for jobs when filtering by tool ID. */
const validFiltersById: Record<string, ValidFilter<string | number>> = {
    tool_id: { placeholder: "tool id", type: String, handler: contains("tool_id"), menuItem: true },
    tool_id_eq: { type: String, handler: equals("tool_id"), menuItem: false },
    ...baseFilters,
};

/** Valid filters for jobs when filtering by tool name. */
const validFiltersByName: Record<string, ValidFilter<string | number>> = {
    name: { placeholder: "tool name", type: String, handler: contains("name"), menuItem: true },
    name_eq: { type: String, handler: equals("name"), menuItem: false },
    ...baseFilters,
};

export const JobsFiltersById = new Filtering(validFiltersById, undefined, true, "tool_id");
export const JobsFiltersByName = new Filtering(validFiltersByName, undefined, true, "name");

/**
 * Tests whether a job still matches the *mutable* part of the filter text it was originally
 * fetched under (state, update time), not tool id/name, which the backend's own search decides
 * once and a job's tool never changes afterwards.
 *
 * Used to drop a job from a filtered view as soon as a live update (e.g. a state change) takes it
 * out of the filter's criteria, instead of leaving it visible until the next re-fetch.
 */
export type JobMatcher = (job: JobBaseModel) => boolean;

/**
 * Turn a `JobsFilters` filter text into query params for `/api/jobs`, plus a client-side matcher
 * for the same criteria (see `JobMatcher`).
 * @param filterText The filter text entered by the user.
 * @param useNameFilter If `false` (by default), we filter by tool ID by passing the provided id
 *                      in the `search: string` parameter. If `true`, we instead find all tools in the
 *                      `toolStore` matching the provided name, and then pass `tool_id: string[]`
 *                      as a parameter.
 */
export function jobsFilterParams(
    filterText: string,
    useNameFilter = false,
): { params: UserJobsQueryParams; matchesJob: JobMatcher } {
    const JobsFilters = useNameFilter ? JobsFiltersByName : JobsFiltersById;

    // Ensure that any invalid filters are detected and reported, because otherwise `Filtering` just
    // drops invalid filters
    const rawFilters = Object.fromEntries(JobsFilters.getFiltersForText(filterText, true, false));
    const { invalidFilters } = JobsFilters.getValidFilters(rawFilters, true);
    const invalidKeys = Object.keys(invalidFilters);
    if (invalidKeys.length > 0) {
        throw new Error(`Invalid filter(s) in query: ${invalidKeys.join(", ")}`);
    }

    const params: UserJobsQueryParams = {};
    /** Checks for the mutable filter criteria (state, update time); see `JobMatcher`. */
    const matchers: JobMatcher[] = [];

    const queryDict = JobsFilters.getQueryDict(filterText);

    if (!useNameFilter) {
        if (queryDict["tool_id-eq"]) {
            params.search = `tool:'${queryDict["tool_id-eq"]}'`;
        } else if (queryDict["tool_id-contains"]) {
            params.search = `tool:${queryDict["tool_id-contains"]}`;
        }
    } else {
        const exact = Boolean(queryDict["name-eq"]);
        const toolName = queryDict[exact ? "name-eq" : "name-contains"] as string | undefined;
        if (toolName) {
            params.tool_id = useToolStore().getToolIdsByName(toolName, exact);

            // If no tool is found, we need to error out and not perform a search at all because the user
            // entered some tool name, but it didn't match any existing tools.
            if (params.tool_id.length === 0) {
                throw new Error(`No tools matched the provided name: ${toolName}`);
            }
            if (params.tool_id.length > MAX_TOOL_NAME_MATCHES) {
                throw new Error(
                    `${params.tool_id.length} tools matched the provided name: ${toolName}. Please refine your search.`,
                );
            }
        }
    }

    const status = JobsFilters.getFilterValue(filterText, "status") as string | undefined;
    const groupStates = status ? STATE_GROUPS[status] : undefined;
    if (groupStates) {
        params.state = groupStates;
        matchers.push((job) => groupStates.includes(job.state));
    } else {
        const state = JobsFilters.getFilterValue(filterText, "state") as string | undefined;
        if (state) {
            params.state = [state];
            matchers.push((job) => job.state === state.toLowerCase());
        }
    }

    const updatedAfter = JobsFilters.getFilterValue(filterText, "update_time_gt") as string | undefined;
    if (updatedAfter) {
        params.date_range_min = updatedAfter;
        matchers.push((job) => job.update_time >= updatedAfter);
    }

    const updatedBefore = JobsFilters.getFilterValue(filterText, "update_time_lt") as string | undefined;
    if (updatedBefore) {
        params.date_range_max = updatedBefore;
        matchers.push((job) => job.update_time <= updatedBefore);
    }

    const matchesJob: JobMatcher = (job) => matchers.every((matcher) => matcher(job));
    return { params, matchesJob };
}
