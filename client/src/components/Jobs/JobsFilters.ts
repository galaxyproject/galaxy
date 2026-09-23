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

    // Ensure that any invalid filters are detected and reported, because otherwise `Filtering` just
    // drops invalid filters
    const rawFilters = Object.fromEntries(JobsFilters.getFiltersForText(filterText, true, false));
    const { invalidFilters } = JobsFilters.getValidFilters(rawFilters, true);
    const invalidKeys = Object.keys(invalidFilters);
    if (invalidKeys.length > 0) {
        throw new Error(`Invalid filter(s) in query: ${invalidKeys.join(", ")}`);
    }

    const params: UserJobsQueryParams = {};

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
