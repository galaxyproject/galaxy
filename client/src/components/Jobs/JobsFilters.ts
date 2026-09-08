import { JOB_STATES, type JobsQueryParams } from "@/api/jobs";
import Filtering, { compare, contains, equals, toDate, type ValidFilter } from "@/utils/filtering";

type UserJobsQueryParams = Pick<NonNullable<JobsQueryParams>, "state" | "date_range_min" | "date_range_max" | "search">;

/** Filters for the jobs list. */
const validFilters: Record<string, ValidFilter<string | number>> = {
    tool: { placeholder: "tool id", type: String, handler: contains("tool"), menuItem: true },
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
    /** Unspecified text (e.g. the user just typing "grep1" with no `key:value` filter), which is
     * sent to the backend `search` param as is, alongside `date_range_min:`/`state:`/etc. */
    unspecified_text: { handler: contains("unspecified_text"), menuItem: false },
};

export const JobsFilters = new Filtering(validFilters, undefined, true, "unspecified_text");

/** Turn a `JobsFilters` filter text into query params for `/api/jobs`. */
export function jobsFilterParams(filterText: string): UserJobsQueryParams {
    const params: UserJobsQueryParams = {};

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

    // `getFilterText` (not `getFilterValue`) so `tool`'s value gets requoted correctly if it
    // contains a space, e.g. `tool:'my tool'`.
    const tool = JobsFilters.getFilterValue(filterText, "tool") as string | undefined;
    const unspecifiedText = JobsFilters.getFilterValue(filterText, "unspecified_text") as string | undefined;

    /** `tool` (the ID filter) and `unspecified_text` as the search filters that get forwarded to the `search` query param. */
    const searchFilters: Record<string, string> = {};
    if (tool !== undefined) {
        searchFilters.tool = tool;
    }
    if (unspecifiedText !== undefined) {
        searchFilters.unspecified_text = unspecifiedText;
    }
    const search = JobsFilters.getFilterText(searchFilters, false, filterText);
    if (search) {
        params.search = search;
    }

    return params;
}
