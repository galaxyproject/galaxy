import Filtering, { compare, contains, expandNameTag, toDate } from "utils/filtering";

const validFilters = {
    name: { placeholder: "name", type: String, handler: contains("name"), menuItem: true },
    tag: { placeholder: "tag", type: String, handler: contains("tags", "tag", expandNameTag), menuItem: true },
    annotation: { placeholder: "annotation", type: String, handler: contains("annotation"), menuItem: true },
    update_time: {
        placeholder: "updated time",
        type: Date,
        handler: compare("update_time", "le", toDate),
        isRangeInput: true,
        menuItem: true,
    },
    update_time_ge: { handler: compare("update_time", "ge", toDate), menuItem: false },
    update_time_le: { handler: compare("update_time", "le", toDate), menuItem: false },
};
export const HistoriesFilters = new Filtering(validFilters);
