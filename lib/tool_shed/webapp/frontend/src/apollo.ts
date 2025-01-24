import { createApolloProvider } from "@vue/apollo-option"
import { ApolloClient, InMemoryCache, DefaultOptions } from "@apollo/client/core"

import { loadErrorMessages, loadDevMessages } from "@apollo/client/dev"

const dev = false
if (dev) {
    // Adds messages only in a dev environment
    loadDevMessages()
    loadErrorMessages()
}

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

export const cache = new InMemoryCache()
export const apolloClient = new ApolloClient({
    uri: "/api/graphql/",
    cache: cache,
    defaultOptions: defaultOptions,
})

export const apolloClientProvider = createApolloProvider({
    defaultClient: apolloClient,
})

// npx apollo schema:download --endpoint=http://localhost:9009/graphql/ graphql-schema.json
