# Galaxy Client API

A standalone client library for the Galaxy API, built using the type definitions from the main Galaxy client.

## Installation

```bash
npm install @galaxyproject/client-api
# or
yarn add @galaxyproject/client-api
# or
pnpm add @galaxyproject/client-api
```

## Usage

```typescript
import { createGalaxyApi } from "@galaxyproject/client-api";

// Create an instance of the Galaxy API client with a specific base URL
const api = createGalaxyApi("https://usegalaxy.org");

// Alternatively, use the default (current origin)
// const api = createGalaxyApi();

// Example: Get a list of histories
const { data, error } = await api.GET("/api/histories");

if (error) {
    console.error("Error fetching histories:", error);
} else {
    console.log("Histories:", data);
}

// For backward compatibility
import { GalaxyApi } from "@galaxyproject/client-api";
const legacyApi = GalaxyApi(); // Uses current origin
```

## Type Safety

This package provides TypeScript types for all Galaxy API endpoints and models:

```typescript
import { createGalaxyApi, type HistorySummary, type DatasetEntry } from "@galaxyproject/client-api";

const api = createGalaxyApi();

// Type-safe API calls
const { data: histories } = await api.GET("/api/histories");
// histories is typed as HistorySummary[] | undefined

// You can use the types for your variables
const myHistory: HistorySummary = {
    id: "123",
    name: "My History",
    // ...other required properties
};
```

## Example

The package includes a simple example in the `src/example.ts` file that demonstrates how to use the client:

```typescript
import { createGalaxyApi } from "@galaxyproject/client-api";

// Create a client with a specific Galaxy instance
const api = createGalaxyApi("https://usegalaxy.org");

// Example: Get a list of tools
async function getTools() {
    const { data, error } = await api.GET("/api/tools");

    if (error) {
        console.error("Error fetching tools:", error);
        return [];
    }

    // Log tool count
    console.log(`Found ${data.length} tools`);

    return data;
}
```

## Design Notes

This package uses symlinks to reference API type definitions from the main Galaxy client while providing a standalone client implementation. This approach was chosen to:

1. Minimize duplication of type definitions
2. Ensure type definitions stay in sync with the main codebase
3. Allow the client to work independently of Galaxy's internal utilities

Key symlinks:

- `src/api` → `../../client/src/api` (for type definitions)
- `src/utils/error.ts` - Custom error handling utilities

## Development

To work on this package:

1. Make changes to the API type definitions in the main Galaxy client
2. The type changes will automatically be available in this package via symlinks
3. Build the library for distribution:

    ```bash
    # Install dependencies
    npm install

    # Build the library
    npm run build

    # Watch mode for development
    npm run dev
    ```

### Testing

The package includes tests built with Vitest:

```bash
# Install dependencies
npm install

# Run tests
npm test

# Run tests with watch mode (during development)
npm run test:watch

# Run tests with coverage report
npm run test:coverage
```

The tests verify:

- Client creation with default and custom base URLs
- Basic API interaction with proper typing
- Error handling
- Backward compatibility with the original API
