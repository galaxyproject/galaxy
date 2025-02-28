import { graphql } from "@/gql"

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
