import { useConfigStore } from "@/stores/configurationStore";

const configStore = useConfigStore();

export interface HelpForumTopic {
	id: number;
	title: string;
	fancy_title: string;
	slug: string;
	posts_count: number;
	reply_count: number;
	highest_post_number: number;
	created_at: string;
	last_posted_at: string;
	bumped: boolean;
	bumped_at: string;
	archetype: unknown;
	unseen: boolean;
	pinned: boolean;
	unpinned: unknown;
	visible: boolean;
	closed: boolean;
	archived: boolean;
	bookmarked: unknown;
	liked: unknown;
	tags: string[];
	tags_descriptions: unknown;
	category_id: number;
	has_accepted_answer: boolean;
}

export interface HelpForumSearchResponseData {
	posts: unknown;
	topics: HelpForumTopic[];
	users: unknown;
	categories: unknown;
	tags: unknown;
	groups: unknown;
	grouped_search_result: unknown;
}

/**
 * Fetch search results from the galaxy help forum
 * https://docs.discourse.org/#tag/Search/operation/search
 * @param term plaintext search
 * @param tags forum tags
 */
export async function search(term: string, tags: string[] = []): Promise<HelpForumSearchResponseData> {
	const apiBaseUrl = configStore.config.help_forum_api_url;
	const apiUrl = new URL("/search.json", apiBaseUrl);

	let query = `${term} order:latest_topic`;

	if (tags.length > 0) {
		query += `tags:${tags.join(",")}`;
	}

	apiUrl.searchParams.append("q", encodeURIComponent(query));

	const res = await fetch(apiUrl);

	return await res.json() as HelpForumSearchResponseData;
}