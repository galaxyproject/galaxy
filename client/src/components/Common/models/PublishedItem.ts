export interface PublishedItem {
    name: string;
    model_class?: string;
    owner?: string;
    username?: string | null;
    email_hash?: string;
    author_deleted?: boolean;
    tags?: string[];
    title?: string;
}
