export interface Item {
    title: string;
    username_and_slug?: `${string}/${string}`;
    importable: boolean;
    published: boolean;
    users_shared_with?: Array<{ email: string }>;
    extra?: {
        cannot_change: Array<{ id: string; name: string }>;
        can_change: Array<{ id: string; name: string }>;
    };
    errors?: string[];
}

export type ShareOption = "make_public" | "make_accessible_to_shared" | "no_changes";
