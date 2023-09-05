export interface Item {
    title: string;
    username_and_slug: `${string}/${string}`;
    importable: boolean;
    published: boolean;
    users_shared_with: Array<{ email: string }>;
    extra?: {
        cannot_change: unknown[];
        can_change: unknown[];
        can_share: boolean;
    };
}
