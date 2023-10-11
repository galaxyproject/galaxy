import Filtering, { compare, contains, equals, expandNameTag, toBool, toDate } from "utils/filtering";

export const validFilters = {
    hid: equals("hid"),
    state: equals("state"),
    name: contains("name"),
    extension: equals("extension"),
    genome_build: contains("genome_build"),
    hid_ge: compare("hid", "ge"),
    hid_gt: compare("hid", "gt"),
    hid_le: compare("hid", "le"),
    hid_lt: compare("hid", "lt"),
    related: equals("related"),
    tag: contains("tags", "tag", expandNameTag),
    visible: equals("visible", "visible", toBool),
    deleted: equals("deleted", "deleted", toBool),
    create_time: compare("create_time", "le", toDate),
    create_time_ge: compare("create_time", "ge", toDate),
    create_time_gt: compare("create_time", "gt", toDate),
    create_time_le: compare("create_time", "le", toDate),
    create_time_lt: compare("create_time", "lt", toDate),
    update_time: compare("update_time", "le", toDate),
    update_time_ge: compare("update_time", "ge", toDate),
    update_time_gt: compare("update_time", "gt", toDate),
    update_time_le: compare("update_time", "le", toDate),
    update_time_lt: compare("update_time", "lt", toDate),
};

export const HistoryFilters = new Filtering(validFilters, true);
