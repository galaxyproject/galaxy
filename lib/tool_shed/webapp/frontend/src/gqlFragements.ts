import { graphql } from "@/gql"

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
