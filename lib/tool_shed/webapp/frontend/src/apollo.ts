import { createApolloProvider } from "@vue/apollo-option"
import { ApolloClient, InMemoryCache, DefaultOptions } from "@apollo/client/core"

const defaultOptions: DefaultOptions = {
    watchQuery: {
        fetchPolicy: "no-cache",
        errorPolicy: "ignore",
    },
    query: {
        fetchPolicy: "no-cache",
        errorPolicy: "all",
    },
}

export const apolloClient = new ApolloClient({
    uri: "/api/graphql/",
    cache: new InMemoryCache(),
    defaultOptions: defaultOptions,
})

export const apolloClientProvider = createApolloProvider({
    defaultClient: apolloClient,
})

// npx apollo schema:download --endpoint=http://localhost:9009/graphql/ graphql-schema.json
