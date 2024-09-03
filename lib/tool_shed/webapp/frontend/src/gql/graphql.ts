/* eslint-disable */
import { TypedDocumentNode as DocumentNode } from "@graphql-typed-document-node/core"
export type Maybe<T> = T | null
export type InputMaybe<T> = Maybe<T>
export type Exact<T extends { [key: string]: unknown }> = { [K in keyof T]: T[K] }
export type MakeOptional<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]?: Maybe<T[SubKey]> }
export type MakeMaybe<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]: Maybe<T[SubKey]> }
/** All built-in and custom scalars, mapped to their actual values */
export type Scalars = {
    ID: string
    String: string
    Boolean: boolean
    Int: number
    Float: number
    /**
     * The `DateTime` scalar type represents a DateTime
     * value as specified by
     * [iso8601](https://en.wikipedia.org/wiki/ISO_8601).
     */
    DateTime: any
}

/** An object with an ID */
export type Node = {
    /** The ID of the object */
    id: Scalars["ID"]
}

/** The Relay compliant `PageInfo` type, containing data necessary to paginate this connection. */
export type PageInfo = {
    __typename?: "PageInfo"
    /** When paginating forwards, the cursor to continue. */
    endCursor?: Maybe<Scalars["String"]>
    /** When paginating forwards, are there more items? */
    hasNextPage: Scalars["Boolean"]
    /** When paginating backwards, are there more items? */
    hasPreviousPage: Scalars["Boolean"]
    /** When paginating backwards, the cursor to continue. */
    startCursor?: Maybe<Scalars["String"]>
}

export type Query = {
    __typename?: "Query"
    categories?: Maybe<Array<Maybe<SimpleCategory>>>
    node?: Maybe<Node>
    relayCategories?: Maybe<RelayCategoryConnection>
    relayRepositories?: Maybe<RelayRepositoryConnection>
    relayRepositoriesForCategory?: Maybe<RelayRepositoryConnection>
    relayRepositoriesForOwner?: Maybe<RelayRepositoryConnection>
    relayRevisions?: Maybe<RelayRepositoryMetadataConnection>
    relayUsers?: Maybe<RelayUserConnection>
    repositories?: Maybe<Array<Maybe<SimpleRepository>>>
    revisions?: Maybe<Array<Maybe<SimpleRepositoryMetadata>>>
    users?: Maybe<Array<Maybe<SimpleUser>>>
}

export type QueryNodeArgs = {
    id: Scalars["ID"]
}

export type QueryRelayCategoriesArgs = {
    after?: InputMaybe<Scalars["String"]>
    before?: InputMaybe<Scalars["String"]>
    first?: InputMaybe<Scalars["Int"]>
    last?: InputMaybe<Scalars["Int"]>
    sort?: InputMaybe<Array<InputMaybe<RelayCategorySortEnum>>>
}

export type QueryRelayRepositoriesArgs = {
    after?: InputMaybe<Scalars["String"]>
    before?: InputMaybe<Scalars["String"]>
    first?: InputMaybe<Scalars["Int"]>
    last?: InputMaybe<Scalars["Int"]>
    sort?: InputMaybe<Array<InputMaybe<RelayRepositorySortEnum>>>
}

export type QueryRelayRepositoriesForCategoryArgs = {
    after?: InputMaybe<Scalars["String"]>
    before?: InputMaybe<Scalars["String"]>
    encodedId?: InputMaybe<Scalars["String"]>
    first?: InputMaybe<Scalars["Int"]>
    id?: InputMaybe<Scalars["Int"]>
    last?: InputMaybe<Scalars["Int"]>
    sort?: InputMaybe<Array<InputMaybe<RelayRepositorySortEnum>>>
}

export type QueryRelayRepositoriesForOwnerArgs = {
    after?: InputMaybe<Scalars["String"]>
    before?: InputMaybe<Scalars["String"]>
    first?: InputMaybe<Scalars["Int"]>
    last?: InputMaybe<Scalars["Int"]>
    sort?: InputMaybe<Array<InputMaybe<RelayRepositorySortEnum>>>
    username?: InputMaybe<Scalars["String"]>
}

export type QueryRelayRevisionsArgs = {
    after?: InputMaybe<Scalars["String"]>
    before?: InputMaybe<Scalars["String"]>
    first?: InputMaybe<Scalars["Int"]>
    last?: InputMaybe<Scalars["Int"]>
    sort?: InputMaybe<Array<InputMaybe<RelayRepositoryMetadataSortEnum>>>
}

export type QueryRelayUsersArgs = {
    after?: InputMaybe<Scalars["String"]>
    before?: InputMaybe<Scalars["String"]>
    first?: InputMaybe<Scalars["Int"]>
    last?: InputMaybe<Scalars["Int"]>
    sort?: InputMaybe<Array<InputMaybe<RelayUserSortEnum>>>
}

export type RelayCategory = Node & {
    __typename?: "RelayCategory"
    createTime?: Maybe<Scalars["DateTime"]>
    deleted?: Maybe<Scalars["Boolean"]>
    description?: Maybe<Scalars["String"]>
    encodedId: Scalars["String"]
    id: Scalars["ID"]
    name: Scalars["String"]
    repositories?: Maybe<Array<Maybe<SimpleRepository>>>
    updateTime?: Maybe<Scalars["DateTime"]>
}

export type RelayCategoryConnection = {
    __typename?: "RelayCategoryConnection"
    /** Contains the nodes in this connection. */
    edges: Array<Maybe<RelayCategoryEdge>>
    /** Pagination data for this connection. */
    pageInfo: PageInfo
}

/** A Relay edge containing a `RelayCategory` and its cursor. */
export type RelayCategoryEdge = {
    __typename?: "RelayCategoryEdge"
    /** A cursor for use in pagination */
    cursor: Scalars["String"]
    /** The item at the end of the edge */
    node?: Maybe<RelayCategory>
}

/** An enumeration. */
export enum RelayCategorySortEnum {
    CreateTimeAsc = "CREATE_TIME_ASC",
    CreateTimeDesc = "CREATE_TIME_DESC",
    DeletedAsc = "DELETED_ASC",
    DeletedDesc = "DELETED_DESC",
    DescriptionAsc = "DESCRIPTION_ASC",
    DescriptionDesc = "DESCRIPTION_DESC",
    IdAsc = "ID_ASC",
    IdDesc = "ID_DESC",
    NameAsc = "NAME_ASC",
    NameDesc = "NAME_DESC",
    UpdateTimeAsc = "UPDATE_TIME_ASC",
    UpdateTimeDesc = "UPDATE_TIME_DESC",
}

export type RelayRepository = Node & {
    __typename?: "RelayRepository"
    categories?: Maybe<Array<Maybe<SimpleCategory>>>
    createTime?: Maybe<Scalars["DateTime"]>
    description?: Maybe<Scalars["String"]>
    encodedId: Scalars["String"]
    homepageUrl?: Maybe<Scalars["String"]>
    id: Scalars["ID"]
    longDescription?: Maybe<Scalars["String"]>
    name: Scalars["String"]
    remoteRepositoryUrl?: Maybe<Scalars["String"]>
    type?: Maybe<Scalars["String"]>
    updateTime?: Maybe<Scalars["DateTime"]>
    user: SimpleUser
}

export type RelayRepositoryConnection = {
    __typename?: "RelayRepositoryConnection"
    /** Contains the nodes in this connection. */
    edges: Array<Maybe<RelayRepositoryEdge>>
    /** Pagination data for this connection. */
    pageInfo: PageInfo
}

/** A Relay edge containing a `RelayRepository` and its cursor. */
export type RelayRepositoryEdge = {
    __typename?: "RelayRepositoryEdge"
    /** A cursor for use in pagination */
    cursor: Scalars["String"]
    /** The item at the end of the edge */
    node?: Maybe<RelayRepository>
}

export type RelayRepositoryMetadata = Node & {
    __typename?: "RelayRepositoryMetadata"
    changesetRevision: Scalars["String"]
    createTime?: Maybe<Scalars["DateTime"]>
    downloadable?: Maybe<Scalars["Boolean"]>
    encodedId: Scalars["String"]
    id: Scalars["ID"]
    malicious?: Maybe<Scalars["Boolean"]>
    numericRevision?: Maybe<Scalars["Int"]>
    repository: SimpleRepository
    updateTime?: Maybe<Scalars["DateTime"]>
}

export type RelayRepositoryMetadataConnection = {
    __typename?: "RelayRepositoryMetadataConnection"
    /** Contains the nodes in this connection. */
    edges: Array<Maybe<RelayRepositoryMetadataEdge>>
    /** Pagination data for this connection. */
    pageInfo: PageInfo
}

/** A Relay edge containing a `RelayRepositoryMetadata` and its cursor. */
export type RelayRepositoryMetadataEdge = {
    __typename?: "RelayRepositoryMetadataEdge"
    /** A cursor for use in pagination */
    cursor: Scalars["String"]
    /** The item at the end of the edge */
    node?: Maybe<RelayRepositoryMetadata>
}

/** An enumeration. */
export enum RelayRepositoryMetadataSortEnum {
    IdAsc = "ID_ASC",
    IdDesc = "ID_DESC",
}

/** An enumeration. */
export enum RelayRepositorySortEnum {
    CreateTimeAsc = "CREATE_TIME_ASC",
    CreateTimeDesc = "CREATE_TIME_DESC",
    DescriptionAsc = "DESCRIPTION_ASC",
    DescriptionDesc = "DESCRIPTION_DESC",
    HomepageUrlAsc = "HOMEPAGE_URL_ASC",
    HomepageUrlDesc = "HOMEPAGE_URL_DESC",
    IdAsc = "ID_ASC",
    IdDesc = "ID_DESC",
    LongDescriptionAsc = "LONG_DESCRIPTION_ASC",
    LongDescriptionDesc = "LONG_DESCRIPTION_DESC",
    NameAsc = "NAME_ASC",
    NameDesc = "NAME_DESC",
    RemoteRepositoryUrlAsc = "REMOTE_REPOSITORY_URL_ASC",
    RemoteRepositoryUrlDesc = "REMOTE_REPOSITORY_URL_DESC",
    TypeAsc = "TYPE_ASC",
    TypeDesc = "TYPE_DESC",
    UpdateTimeAsc = "UPDATE_TIME_ASC",
    UpdateTimeDesc = "UPDATE_TIME_DESC",
}

export type RelayUser = Node & {
    __typename?: "RelayUser"
    encodedId: Scalars["String"]
    id: Scalars["ID"]
    username: Scalars["String"]
}

export type RelayUserConnection = {
    __typename?: "RelayUserConnection"
    /** Contains the nodes in this connection. */
    edges: Array<Maybe<RelayUserEdge>>
    /** Pagination data for this connection. */
    pageInfo: PageInfo
}

/** A Relay edge containing a `RelayUser` and its cursor. */
export type RelayUserEdge = {
    __typename?: "RelayUserEdge"
    /** A cursor for use in pagination */
    cursor: Scalars["String"]
    /** The item at the end of the edge */
    node?: Maybe<RelayUser>
}

/** An enumeration. */
export enum RelayUserSortEnum {
    IdAsc = "ID_ASC",
    IdDesc = "ID_DESC",
    UsernameAsc = "USERNAME_ASC",
    UsernameDesc = "USERNAME_DESC",
}

export type SimpleCategory = {
    __typename?: "SimpleCategory"
    createTime?: Maybe<Scalars["DateTime"]>
    deleted?: Maybe<Scalars["Boolean"]>
    description?: Maybe<Scalars["String"]>
    encodedId: Scalars["String"]
    id: Scalars["ID"]
    name: Scalars["String"]
    repositories?: Maybe<Array<Maybe<SimpleRepository>>>
    updateTime?: Maybe<Scalars["DateTime"]>
}

export type SimpleRepository = {
    __typename?: "SimpleRepository"
    categories?: Maybe<Array<Maybe<SimpleCategory>>>
    createTime?: Maybe<Scalars["DateTime"]>
    description?: Maybe<Scalars["String"]>
    downloadableRevisions?: Maybe<Array<Maybe<SimpleRepositoryMetadata>>>
    encodedId: Scalars["String"]
    homepageUrl?: Maybe<Scalars["String"]>
    id: Scalars["ID"]
    longDescription?: Maybe<Scalars["String"]>
    metadataRevisions?: Maybe<Array<Maybe<SimpleRepositoryMetadata>>>
    name: Scalars["String"]
    remoteRepositoryUrl?: Maybe<Scalars["String"]>
    type?: Maybe<Scalars["String"]>
    updateTime?: Maybe<Scalars["DateTime"]>
    user: SimpleUser
}

export type SimpleRepositoryMetadata = {
    __typename?: "SimpleRepositoryMetadata"
    changesetRevision: Scalars["String"]
    createTime?: Maybe<Scalars["DateTime"]>
    downloadable?: Maybe<Scalars["Boolean"]>
    encodedId: Scalars["String"]
    id: Scalars["ID"]
    malicious?: Maybe<Scalars["Boolean"]>
    numericRevision?: Maybe<Scalars["Int"]>
    repository: SimpleRepository
    updateTime?: Maybe<Scalars["DateTime"]>
}

export type SimpleUser = {
    __typename?: "SimpleUser"
    encodedId: Scalars["String"]
    id: Scalars["ID"]
    username: Scalars["String"]
}

export type RecentlyCreatedRepositoriesQueryVariables = Exact<{ [key: string]: never }>

export type RecentlyCreatedRepositoriesQuery = {
    __typename?: "Query"
    relayRepositories?: {
        __typename?: "RelayRepositoryConnection"
        edges: Array<{
            __typename?: "RelayRepositoryEdge"
            node?:
                | ({ __typename?: "RelayRepository" } & {
                      " $fragmentRefs"?: { RepositoryCreationItemFragment: RepositoryCreationItemFragment }
                  })
                | null
        } | null>
    } | null
}

export type RecentRepositoryUpdatesQueryVariables = Exact<{ [key: string]: never }>

export type RecentRepositoryUpdatesQuery = {
    __typename?: "Query"
    relayRepositories?: {
        __typename?: "RelayRepositoryConnection"
        edges: Array<{
            __typename?: "RelayRepositoryEdge"
            node?:
                | ({ __typename?: "RelayRepository" } & {
                      " $fragmentRefs"?: { RepositoryUpdateItemFragment: RepositoryUpdateItemFragment }
                  })
                | null
        } | null>
    } | null
}

export type RepositoriesByOwnerQueryVariables = Exact<{
    username?: InputMaybe<Scalars["String"]>
    cursor?: InputMaybe<Scalars["String"]>
}>

export type RepositoriesByOwnerQuery = {
    __typename?: "Query"
    relayRepositoriesForOwner?: {
        __typename?: "RelayRepositoryConnection"
        edges: Array<{
            __typename?: "RelayRepositoryEdge"
            cursor: string
            node?:
                | ({ __typename?: "RelayRepository" } & {
                      " $fragmentRefs"?: { RepositoryListItemFragmentFragment: RepositoryListItemFragmentFragment }
                  })
                | null
        } | null>
        pageInfo: { __typename?: "PageInfo"; endCursor?: string | null; hasNextPage: boolean }
    } | null
}

export type RepositoriesByCategoryQueryVariables = Exact<{
    categoryId?: InputMaybe<Scalars["String"]>
    cursor?: InputMaybe<Scalars["String"]>
}>

export type RepositoriesByCategoryQuery = {
    __typename?: "Query"
    relayRepositoriesForCategory?: {
        __typename?: "RelayRepositoryConnection"
        edges: Array<{
            __typename?: "RelayRepositoryEdge"
            cursor: string
            node?:
                | ({ __typename?: "RelayRepository" } & {
                      " $fragmentRefs"?: { RepositoryListItemFragmentFragment: RepositoryListItemFragmentFragment }
                  })
                | null
        } | null>
        pageInfo: { __typename?: "PageInfo"; endCursor?: string | null; hasNextPage: boolean }
    } | null
}

export type RepositoryListItemFragmentFragment = {
    __typename?: "RelayRepository"
    encodedId: string
    name: string
    description?: string | null
    type?: string | null
    updateTime?: any | null
    homepageUrl?: string | null
    remoteRepositoryUrl?: string | null
    user: { __typename?: "SimpleUser"; username: string }
} & { " $fragmentName"?: "RepositoryListItemFragmentFragment" }

export type RepositoryUpdateItemFragment = {
    __typename?: "RelayRepository"
    encodedId: string
    name: string
    updateTime?: any | null
    user: { __typename?: "SimpleUser"; username: string }
} & { " $fragmentName"?: "RepositoryUpdateItemFragment" }

export type RepositoryCreationItemFragment = {
    __typename?: "RelayRepository"
    encodedId: string
    name: string
    createTime?: any | null
    user: { __typename?: "SimpleUser"; username: string }
} & { " $fragmentName"?: "RepositoryCreationItemFragment" }

export const RepositoryListItemFragmentFragmentDoc = {
    kind: "Document",
    definitions: [
        {
            kind: "FragmentDefinition",
            name: { kind: "Name", value: "RepositoryListItemFragment" },
            typeCondition: { kind: "NamedType", name: { kind: "Name", value: "RelayRepository" } },
            selectionSet: {
                kind: "SelectionSet",
                selections: [
                    { kind: "Field", name: { kind: "Name", value: "encodedId" } },
                    { kind: "Field", name: { kind: "Name", value: "name" } },
                    {
                        kind: "Field",
                        name: { kind: "Name", value: "user" },
                        selectionSet: {
                            kind: "SelectionSet",
                            selections: [{ kind: "Field", name: { kind: "Name", value: "username" } }],
                        },
                    },
                    { kind: "Field", name: { kind: "Name", value: "description" } },
                    { kind: "Field", name: { kind: "Name", value: "type" } },
                    { kind: "Field", name: { kind: "Name", value: "updateTime" } },
                    { kind: "Field", name: { kind: "Name", value: "homepageUrl" } },
                    { kind: "Field", name: { kind: "Name", value: "remoteRepositoryUrl" } },
                ],
            },
        },
    ],
} as unknown as DocumentNode<RepositoryListItemFragmentFragment, unknown>
export const RepositoryUpdateItemFragmentDoc = {
    kind: "Document",
    definitions: [
        {
            kind: "FragmentDefinition",
            name: { kind: "Name", value: "RepositoryUpdateItem" },
            typeCondition: { kind: "NamedType", name: { kind: "Name", value: "RelayRepository" } },
            selectionSet: {
                kind: "SelectionSet",
                selections: [
                    { kind: "Field", name: { kind: "Name", value: "encodedId" } },
                    { kind: "Field", name: { kind: "Name", value: "name" } },
                    {
                        kind: "Field",
                        name: { kind: "Name", value: "user" },
                        selectionSet: {
                            kind: "SelectionSet",
                            selections: [{ kind: "Field", name: { kind: "Name", value: "username" } }],
                        },
                    },
                    { kind: "Field", name: { kind: "Name", value: "updateTime" } },
                ],
            },
        },
    ],
} as unknown as DocumentNode<RepositoryUpdateItemFragment, unknown>
export const RepositoryCreationItemFragmentDoc = {
    kind: "Document",
    definitions: [
        {
            kind: "FragmentDefinition",
            name: { kind: "Name", value: "RepositoryCreationItem" },
            typeCondition: { kind: "NamedType", name: { kind: "Name", value: "RelayRepository" } },
            selectionSet: {
                kind: "SelectionSet",
                selections: [
                    { kind: "Field", name: { kind: "Name", value: "encodedId" } },
                    { kind: "Field", name: { kind: "Name", value: "name" } },
                    {
                        kind: "Field",
                        name: { kind: "Name", value: "user" },
                        selectionSet: {
                            kind: "SelectionSet",
                            selections: [{ kind: "Field", name: { kind: "Name", value: "username" } }],
                        },
                    },
                    { kind: "Field", name: { kind: "Name", value: "createTime" } },
                ],
            },
        },
    ],
} as unknown as DocumentNode<RepositoryCreationItemFragment, unknown>
export const RecentlyCreatedRepositoriesDocument = {
    kind: "Document",
    definitions: [
        {
            kind: "OperationDefinition",
            operation: "query",
            name: { kind: "Name", value: "recentlyCreatedRepositories" },
            selectionSet: {
                kind: "SelectionSet",
                selections: [
                    {
                        kind: "Field",
                        name: { kind: "Name", value: "relayRepositories" },
                        arguments: [
                            {
                                kind: "Argument",
                                name: { kind: "Name", value: "first" },
                                value: { kind: "IntValue", value: "10" },
                            },
                            {
                                kind: "Argument",
                                name: { kind: "Name", value: "sort" },
                                value: { kind: "EnumValue", value: "CREATE_TIME_DESC" },
                            },
                        ],
                        selectionSet: {
                            kind: "SelectionSet",
                            selections: [
                                {
                                    kind: "Field",
                                    name: { kind: "Name", value: "edges" },
                                    selectionSet: {
                                        kind: "SelectionSet",
                                        selections: [
                                            {
                                                kind: "Field",
                                                name: { kind: "Name", value: "node" },
                                                selectionSet: {
                                                    kind: "SelectionSet",
                                                    selections: [
                                                        {
                                                            kind: "FragmentSpread",
                                                            name: { kind: "Name", value: "RepositoryCreationItem" },
                                                        },
                                                    ],
                                                },
                                            },
                                        ],
                                    },
                                },
                            ],
                        },
                    },
                ],
            },
        },
        ...RepositoryCreationItemFragmentDoc.definitions,
    ],
} as unknown as DocumentNode<RecentlyCreatedRepositoriesQuery, RecentlyCreatedRepositoriesQueryVariables>
export const RecentRepositoryUpdatesDocument = {
    kind: "Document",
    definitions: [
        {
            kind: "OperationDefinition",
            operation: "query",
            name: { kind: "Name", value: "recentRepositoryUpdates" },
            selectionSet: {
                kind: "SelectionSet",
                selections: [
                    {
                        kind: "Field",
                        name: { kind: "Name", value: "relayRepositories" },
                        arguments: [
                            {
                                kind: "Argument",
                                name: { kind: "Name", value: "first" },
                                value: { kind: "IntValue", value: "10" },
                            },
                            {
                                kind: "Argument",
                                name: { kind: "Name", value: "sort" },
                                value: { kind: "EnumValue", value: "UPDATE_TIME_DESC" },
                            },
                        ],
                        selectionSet: {
                            kind: "SelectionSet",
                            selections: [
                                {
                                    kind: "Field",
                                    name: { kind: "Name", value: "edges" },
                                    selectionSet: {
                                        kind: "SelectionSet",
                                        selections: [
                                            {
                                                kind: "Field",
                                                name: { kind: "Name", value: "node" },
                                                selectionSet: {
                                                    kind: "SelectionSet",
                                                    selections: [
                                                        {
                                                            kind: "FragmentSpread",
                                                            name: { kind: "Name", value: "RepositoryUpdateItem" },
                                                        },
                                                    ],
                                                },
                                            },
                                        ],
                                    },
                                },
                            ],
                        },
                    },
                ],
            },
        },
        ...RepositoryUpdateItemFragmentDoc.definitions,
    ],
} as unknown as DocumentNode<RecentRepositoryUpdatesQuery, RecentRepositoryUpdatesQueryVariables>
export const RepositoriesByOwnerDocument = {
    kind: "Document",
    definitions: [
        {
            kind: "OperationDefinition",
            operation: "query",
            name: { kind: "Name", value: "repositoriesByOwner" },
            variableDefinitions: [
                {
                    kind: "VariableDefinition",
                    variable: { kind: "Variable", name: { kind: "Name", value: "username" } },
                    type: { kind: "NamedType", name: { kind: "Name", value: "String" } },
                },
                {
                    kind: "VariableDefinition",
                    variable: { kind: "Variable", name: { kind: "Name", value: "cursor" } },
                    type: { kind: "NamedType", name: { kind: "Name", value: "String" } },
                },
            ],
            selectionSet: {
                kind: "SelectionSet",
                selections: [
                    {
                        kind: "Field",
                        name: { kind: "Name", value: "relayRepositoriesForOwner" },
                        arguments: [
                            {
                                kind: "Argument",
                                name: { kind: "Name", value: "username" },
                                value: { kind: "Variable", name: { kind: "Name", value: "username" } },
                            },
                            {
                                kind: "Argument",
                                name: { kind: "Name", value: "sort" },
                                value: { kind: "EnumValue", value: "UPDATE_TIME_DESC" },
                            },
                            {
                                kind: "Argument",
                                name: { kind: "Name", value: "first" },
                                value: { kind: "IntValue", value: "10" },
                            },
                            {
                                kind: "Argument",
                                name: { kind: "Name", value: "after" },
                                value: { kind: "Variable", name: { kind: "Name", value: "cursor" } },
                            },
                        ],
                        selectionSet: {
                            kind: "SelectionSet",
                            selections: [
                                {
                                    kind: "Field",
                                    name: { kind: "Name", value: "edges" },
                                    selectionSet: {
                                        kind: "SelectionSet",
                                        selections: [
                                            { kind: "Field", name: { kind: "Name", value: "cursor" } },
                                            {
                                                kind: "Field",
                                                name: { kind: "Name", value: "node" },
                                                selectionSet: {
                                                    kind: "SelectionSet",
                                                    selections: [
                                                        {
                                                            kind: "FragmentSpread",
                                                            name: { kind: "Name", value: "RepositoryListItemFragment" },
                                                        },
                                                    ],
                                                },
                                            },
                                        ],
                                    },
                                },
                                {
                                    kind: "Field",
                                    name: { kind: "Name", value: "pageInfo" },
                                    selectionSet: {
                                        kind: "SelectionSet",
                                        selections: [
                                            { kind: "Field", name: { kind: "Name", value: "endCursor" } },
                                            { kind: "Field", name: { kind: "Name", value: "hasNextPage" } },
                                        ],
                                    },
                                },
                            ],
                        },
                    },
                ],
            },
        },
        ...RepositoryListItemFragmentFragmentDoc.definitions,
    ],
} as unknown as DocumentNode<RepositoriesByOwnerQuery, RepositoriesByOwnerQueryVariables>
export const RepositoriesByCategoryDocument = {
    kind: "Document",
    definitions: [
        {
            kind: "OperationDefinition",
            operation: "query",
            name: { kind: "Name", value: "repositoriesByCategory" },
            variableDefinitions: [
                {
                    kind: "VariableDefinition",
                    variable: { kind: "Variable", name: { kind: "Name", value: "categoryId" } },
                    type: { kind: "NamedType", name: { kind: "Name", value: "String" } },
                },
                {
                    kind: "VariableDefinition",
                    variable: { kind: "Variable", name: { kind: "Name", value: "cursor" } },
                    type: { kind: "NamedType", name: { kind: "Name", value: "String" } },
                },
            ],
            selectionSet: {
                kind: "SelectionSet",
                selections: [
                    {
                        kind: "Field",
                        name: { kind: "Name", value: "relayRepositoriesForCategory" },
                        arguments: [
                            {
                                kind: "Argument",
                                name: { kind: "Name", value: "encodedId" },
                                value: { kind: "Variable", name: { kind: "Name", value: "categoryId" } },
                            },
                            {
                                kind: "Argument",
                                name: { kind: "Name", value: "sort" },
                                value: { kind: "EnumValue", value: "UPDATE_TIME_DESC" },
                            },
                            {
                                kind: "Argument",
                                name: { kind: "Name", value: "first" },
                                value: { kind: "IntValue", value: "10" },
                            },
                            {
                                kind: "Argument",
                                name: { kind: "Name", value: "after" },
                                value: { kind: "Variable", name: { kind: "Name", value: "cursor" } },
                            },
                        ],
                        selectionSet: {
                            kind: "SelectionSet",
                            selections: [
                                {
                                    kind: "Field",
                                    name: { kind: "Name", value: "edges" },
                                    selectionSet: {
                                        kind: "SelectionSet",
                                        selections: [
                                            { kind: "Field", name: { kind: "Name", value: "cursor" } },
                                            {
                                                kind: "Field",
                                                name: { kind: "Name", value: "node" },
                                                selectionSet: {
                                                    kind: "SelectionSet",
                                                    selections: [
                                                        {
                                                            kind: "FragmentSpread",
                                                            name: { kind: "Name", value: "RepositoryListItemFragment" },
                                                        },
                                                    ],
                                                },
                                            },
                                        ],
                                    },
                                },
                                {
                                    kind: "Field",
                                    name: { kind: "Name", value: "pageInfo" },
                                    selectionSet: {
                                        kind: "SelectionSet",
                                        selections: [
                                            { kind: "Field", name: { kind: "Name", value: "endCursor" } },
                                            { kind: "Field", name: { kind: "Name", value: "hasNextPage" } },
                                        ],
                                    },
                                },
                            ],
                        },
                    },
                ],
            },
        },
        ...RepositoryListItemFragmentFragmentDoc.definitions,
    ],
} as unknown as DocumentNode<RepositoriesByCategoryQuery, RepositoriesByCategoryQueryVariables>
