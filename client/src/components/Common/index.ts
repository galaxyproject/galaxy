// TODO: Not sure if this is the best place for this type
export type ColorVariant = "primary" | "secondary" | "success" | "danger" | "warning" | "info" | "light" | "dark";

export type ListView = "grid" | "list";

export type SortBy = "create_time" | "update_time" | "name";

export type SortKey = {
    label: string;
    key: SortBy;
};

export const defaultSortKeys: SortKey[] = [
    { label: "Name", key: "name" },
    { label: "Update time", key: "update_time" },
];
