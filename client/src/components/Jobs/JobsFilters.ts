import { JOB_STATES, type JobsQueryParams } from "@/api/jobs";
import { useToolStore } from "@/stores/toolStore";
import Filtering, { compare, contains, equals, toDate, type ValidFilter } from "@/utils/filtering";

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
 * Turn a `JobsFilters` filter text into query params for `/api/jobs`.
 * @param filterText The filter text entered by the user.
 * @param useNameFilter If `false` (by default), we filter by tool ID by passing the provided id
 *                      in the `search: string` parameter. If `true`, we instead find all tools in the
 *                      `toolStore` matching the provided name, and then pass `tool_id: string[]`
 *                      as a parameter.
 */
export function jobsFilterParams(filterText: string, useNameFilter = false): UserJobsQueryParams {
    const JobsFilters = useNameFilter ? JobsFiltersByName : JobsFiltersById;

    const params: UserJobsQueryParams = {};

    if (!useNameFilter) {
        const toolId = JobsFilters.getFilterValue(filterText, "tool_id") as string | undefined;
        if (toolId) {
            // We need to check the query dict for whether the exact match filter `tool_id-eq` is present
            // (to quote the tool ID correctly)
            const queryDict = JobsFilters.getQueryDict(filterText);
            if (queryDict["tool_id-eq"]) {
                params.search = `tool:'${toolId}'`;
            } else {
                params.search = `tool:${toolId}`;
            }
        }
    } else {
        const toolName = JobsFilters.getFilterValue(filterText, "name") as string | undefined;
        if (toolName) {
            const queryDict = JobsFilters.getQueryDict(filterText);
            params.tool_id = useToolStore().getToolIdsByName(toolName, Boolean(queryDict["name-eq"]));

            // If no tool is found, we need to error out and not perform a search at all because the user
            // entered some tool name, but it didn't match any existing tools.
            if (params.tool_id.length === 0) {
                throw new Error(`No tools matched the provided name: ${toolName}`);
            }
        }
    }

    const state = JobsFilters.getFilterValue(filterText, "state") as string | undefined;
    if (state) {
        params.state = [state];
    }

    const updatedAfter = JobsFilters.getFilterValue(filterText, "update_time_gt") as string | undefined;
    if (updatedAfter) {
        params.date_range_min = updatedAfter;
    }

    const updatedBefore = JobsFilters.getFilterValue(filterText, "update_time_lt") as string | undefined;
    if (updatedBefore) {
        params.date_range_max = updatedBefore;
    }

    return params;
}
