import { JOB_STATES } from "@/api/jobs";
import Filtering, { compare, contains, equals, toDate, type ValidFilter } from "@/utils/filtering";

/** Filters for the jobs list. */
const validFilters: Record<string, ValidFilter<string | number>> = {
    tool_id: { placeholder: "tool id", type: String, handler: contains("tool_id"), menuItem: true },
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

export const JobsFilters = new Filtering(validFilters);

/** Turn a `JobsFilters` filter text into query params for `/api/jobs`. */
export function jobsFilterParams(filterText: string): Record<string, unknown> {
    const params: Record<string, unknown> = {};

    const state = JobsFilters.getFilterValue(filterText, "state");
    if (state) {
        params.state = [state];
    }

    const updatedAfter = JobsFilters.getFilterValue(filterText, "update_time_gt");
    if (updatedAfter) {
        params.date_range_min = updatedAfter;
    }

    const updatedBefore = JobsFilters.getFilterValue(filterText, "update_time_lt");
    if (updatedBefore) {
        params.date_range_max = updatedBefore;
    }
    
    const searchTerms = [];
    const toolId = JobsFilters.getFilterValue(filterText, "tool_id");
    if (toolId) {
        searchTerms.push(`tool:${toolId}`);
    }
    const freeText = JobsFilters.getFilterValue(filterText, "name");
    if (freeText) {
        searchTerms.push(freeText);
    }
    if (searchTerms.length) {
        params.search = searchTerms.join(" ");
    }

    return params;
}
