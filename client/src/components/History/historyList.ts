import Filtering, { contains, equals, expandNameTag, toBool } from "@/utils/filtering";

export function getHistoryListFilters(activeList: "my" | "shared" | "published" | "archived" = "my") {
    const validFilters = {
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
    } as const;

    const publishedFilter = {
        published: {
            placeholder: "Published",
            type: Boolean,
            boolType: "is" as const,
            handler: equals("published", "published", toBool),
            menuItem: true,
        },
    };

    if (activeList === "my") {
        return new Filtering(
            {
                ...validFilters,
                ...publishedFilter,
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
            false,
        );
    } else {
        return new Filtering(
            {
                ...validFilters,
                ...(activeList !== "published" ? publishedFilter : {}),
                user: {
                    placeholder: "user",
                    type: String,
                    handler: contains("username"),
                    menuItem: true,
                },
            },
            undefined,
            false,
            false,
        );
    }
}
