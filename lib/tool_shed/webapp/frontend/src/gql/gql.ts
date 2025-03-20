/* eslint-disable */
import * as types from "./graphql"
import { TypedDocumentNode as DocumentNode } from "@graphql-typed-document-node/core"

/**
 * Map of all GraphQL operations in the project.
 *
 * This map has several performance disadvantages:
 * 1. It is not tree-shakeable, so it will include all operations in the project.
 * 2. It is not minifiable, so the string of a GraphQL query will be multiple times inside the bundle.
 * 3. It does not support dead code elimination, so it will add unused operations.
 *
 * Therefore it is highly recommended to use the babel-plugin for production.
 */
const documents = {
    "\n    query recentlyCreatedRepositories {\n        relayRepositories(first: 10, sort: CREATE_TIME_DESC) {\n            edges {\n                node {\n                    ...RepositoryCreationItem\n                }\n            }\n        }\n    }\n":
        types.RecentlyCreatedRepositoriesDocument,
    "\n    query recentRepositoryUpdates {\n        relayRepositories(first: 10, sort: UPDATE_TIME_DESC) {\n            edges {\n                node {\n                    ...RepositoryUpdateItem\n                }\n            }\n        }\n    }\n":
        types.RecentRepositoryUpdatesDocument,
    "\n    query repositoriesByOwner($username: String, $cursor: String) {\n        relayRepositoriesForOwner(username: $username, sort: UPDATE_TIME_DESC, first: 10, after: $cursor) {\n            edges {\n                cursor\n                node {\n                    ...RepositoryListItemFragment\n                }\n            }\n            pageInfo {\n                endCursor\n                hasNextPage\n            }\n        }\n    }\n":
        types.RepositoriesByOwnerDocument,
    "\n    query repositoriesByCategory($categoryId: String, $cursor: String) {\n        relayRepositoriesForCategory(encodedId: $categoryId, sort: NAME_ASC, first: 10, after: $cursor) {\n            edges {\n                cursor\n                node {\n                    ...RepositoryListItemFragment\n                }\n            }\n            pageInfo {\n                endCursor\n                hasNextPage\n            }\n        }\n    }\n":
        types.RepositoriesByCategoryDocument,
    "\n    fragment RepositoryListItemFragment on RelayRepository {\n        encodedId\n        name\n        user {\n            username\n        }\n        description\n        type\n        updateTime\n        homepageUrl\n        remoteRepositoryUrl\n    }\n":
        types.RepositoryListItemFragmentFragmentDoc,
    "\n    fragment RepositoryUpdateItem on RelayRepository {\n        encodedId\n        name\n        user {\n            username\n        }\n        updateTime\n    }\n":
        types.RepositoryUpdateItemFragmentDoc,
    "\n    fragment RepositoryCreationItem on RelayRepository {\n        encodedId\n        name\n        user {\n            username\n        }\n        createTime\n    }\n":
        types.RepositoryCreationItemFragmentDoc,
}

/**
 * The graphql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 *
 *
 * @example
 * ```ts
 * const query = gql(`query GetUser($id: ID!) { user(id: $id) { name } }`);
 * ```
 *
 * The query argument is unknown!
 * Please regenerate the types.
 */
export function graphql(source: string): unknown

/**
 * The graphql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function graphql(
    source: "\n    query recentlyCreatedRepositories {\n        relayRepositories(first: 10, sort: CREATE_TIME_DESC) {\n            edges {\n                node {\n                    ...RepositoryCreationItem\n                }\n            }\n        }\n    }\n"
): (typeof documents)["\n    query recentlyCreatedRepositories {\n        relayRepositories(first: 10, sort: CREATE_TIME_DESC) {\n            edges {\n                node {\n                    ...RepositoryCreationItem\n                }\n            }\n        }\n    }\n"]
/**
 * The graphql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function graphql(
    source: "\n    query recentRepositoryUpdates {\n        relayRepositories(first: 10, sort: UPDATE_TIME_DESC) {\n            edges {\n                node {\n                    ...RepositoryUpdateItem\n                }\n            }\n        }\n    }\n"
): (typeof documents)["\n    query recentRepositoryUpdates {\n        relayRepositories(first: 10, sort: UPDATE_TIME_DESC) {\n            edges {\n                node {\n                    ...RepositoryUpdateItem\n                }\n            }\n        }\n    }\n"]
/**
 * The graphql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function graphql(
    source: "\n    query repositoriesByOwner($username: String, $cursor: String) {\n        relayRepositoriesForOwner(username: $username, sort: UPDATE_TIME_DESC, first: 10, after: $cursor) {\n            edges {\n                cursor\n                node {\n                    ...RepositoryListItemFragment\n                }\n            }\n            pageInfo {\n                endCursor\n                hasNextPage\n            }\n        }\n    }\n"
): (typeof documents)["\n    query repositoriesByOwner($username: String, $cursor: String) {\n        relayRepositoriesForOwner(username: $username, sort: UPDATE_TIME_DESC, first: 10, after: $cursor) {\n            edges {\n                cursor\n                node {\n                    ...RepositoryListItemFragment\n                }\n            }\n            pageInfo {\n                endCursor\n                hasNextPage\n            }\n        }\n    }\n"]
/**
 * The graphql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function graphql(
    source: "\n    query repositoriesByCategory($categoryId: String, $cursor: String) {\n        relayRepositoriesForCategory(encodedId: $categoryId, sort: NAME_ASC, first: 10, after: $cursor) {\n            edges {\n                cursor\n                node {\n                    ...RepositoryListItemFragment\n                }\n            }\n            pageInfo {\n                endCursor\n                hasNextPage\n            }\n        }\n    }\n"
): (typeof documents)["\n    query repositoriesByCategory($categoryId: String, $cursor: String) {\n        relayRepositoriesForCategory(encodedId: $categoryId, sort: NAME_ASC, first: 10, after: $cursor) {\n            edges {\n                cursor\n                node {\n                    ...RepositoryListItemFragment\n                }\n            }\n            pageInfo {\n                endCursor\n                hasNextPage\n            }\n        }\n    }\n"]
/**
 * The graphql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function graphql(
    source: "\n    fragment RepositoryListItemFragment on RelayRepository {\n        encodedId\n        name\n        user {\n            username\n        }\n        description\n        type\n        updateTime\n        homepageUrl\n        remoteRepositoryUrl\n    }\n"
): (typeof documents)["\n    fragment RepositoryListItemFragment on RelayRepository {\n        encodedId\n        name\n        user {\n            username\n        }\n        description\n        type\n        updateTime\n        homepageUrl\n        remoteRepositoryUrl\n    }\n"]
/**
 * The graphql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function graphql(
    source: "\n    fragment RepositoryUpdateItem on RelayRepository {\n        encodedId\n        name\n        user {\n            username\n        }\n        updateTime\n    }\n"
): (typeof documents)["\n    fragment RepositoryUpdateItem on RelayRepository {\n        encodedId\n        name\n        user {\n            username\n        }\n        updateTime\n    }\n"]
/**
 * The graphql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function graphql(
    source: "\n    fragment RepositoryCreationItem on RelayRepository {\n        encodedId\n        name\n        user {\n            username\n        }\n        createTime\n    }\n"
): (typeof documents)["\n    fragment RepositoryCreationItem on RelayRepository {\n        encodedId\n        name\n        user {\n            username\n        }\n        createTime\n    }\n"]

export function graphql(source: string) {
    return (documents as any)[source] ?? {}
}

export type DocumentType<TDocumentNode extends DocumentNode<any, any>> = TDocumentNode extends DocumentNode<
    infer TType,
    any
>
    ? TType
    : never
