import { JOB_STATES, type JobsQueryParams } from "@/api/jobs";
import Filtering, { compare, contains, equals, toDate, type ValidFilter } from "@/utils/filtering";

type UserJobsQueryParams = Pick<NonNullable<JobsQueryParams>, "state" | "date_range_min" | "date_range_max" | "search">;

/** Filters for the jobs list. */
const validFilters: Record<string, ValidFilter<string | number>> = {
    tool_id: { placeholder: "tool id", type: String, handler: contains("tool_id"), menuItem: true },
    tool_id_eq: { type: String, handler: equals("tool_id"), menuItem: false },
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

export const JobsFilters = new Filtering(validFilters, undefined, true, "tool_id");

/** Turn a `JobsFilters` filter text into query params for `/api/jobs`. */
export function jobsFilterParams(filterText: string): UserJobsQueryParams {
    const params: UserJobsQueryParams = {};

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
