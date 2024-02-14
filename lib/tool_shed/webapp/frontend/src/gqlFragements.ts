import { graphql } from "@/gql"

export const RepositoryListItemFragment = graphql(/* GraphQL */ `
    fragment RepositoryListItemFragment on RelayRepository {
        encodedId
        name
        user {
            username
        }
        description
        type
        updateTime
        homepageUrl
        remoteRepositoryUrl
    }
`)

export const UpdateFragment = graphql(/* GraphQL */ `
    fragment RepositoryUpdateItem on RelayRepository {
        encodedId
        name
        user {
            username
        }
        updateTime
    }
`)

export const CreateFragment = graphql(/* GraphQL */ `
    fragment RepositoryCreationItem on RelayRepository {
        encodedId
        name
        user {
            username
        }
        createTime
    }
`)
