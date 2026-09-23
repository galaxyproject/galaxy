import Filtering, { contains, equals, expandNameTag, toBool, type ValidFilter } from "@/utils/filtering";

export function getHistoryListFilters(activeList = "my"): Filtering<string | boolean | undefined> {
    const validFilters: Record<string, ValidFilter<string | boolean | undefined>> = {
        name: {
            placeholder: "name",
            type: String,
            handler: contains("name"),
            menuItem: true,
        },
        tag: {
            placeholder: "tag(s)",
            type: "MultiTags",
            handler: contains("tag", "tag", expandNameTag),
            menuItem: true,
        },
        tool_id: { placeholder: "tool ID", type: String, handler: contains("tool_id"), menuItem: true },
        published: {
            placeholder: "Published",
            type: Boolean,
            boolType: "is",
            handler: equals("published", "published", toBool),
            menuItem: true,
        },
    };

    if (activeList === "my") {
        return new Filtering(
            {
                ...validFilters,
                importable: {
                    placeholder: "Importable",
                    type: Boolean,
                    boolType: "is",
                    handler: equals("importable", "importable", toBool),
                    menuItem: true,
                },
                deleted: {
                    placeholder: "Deleted",
                    type: Boolean,
                    boolType: "is",
                    handler: equals("deleted", "deleted", toBool),
                    menuItem: true,
                },
                purged: {
                    placeholder: "Purged",
                    type: Boolean,
                    boolType: "is",
                    handler: equals("purged", "purged", toBool),
                    menuItem: true,
                },
            },
            undefined,
            false,
            "name",
        );
    } else {
        return new Filtering(
            {
                ...validFilters,
                user: {
                    placeholder: "user",
                    type: String,
                    handler: contains("username"),
                    menuItem: true,
                },
            },
            undefined,
            false,
            "name",
        );
    }
}
