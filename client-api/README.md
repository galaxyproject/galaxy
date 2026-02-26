# Galaxy API Client

A standalone client library for the Galaxy API, built using the type definitions from the main Galaxy client.

## Installation

```bash
npm install @galaxyproject/galaxy-api-client
```

## Usage

### Basic Usage

```typescript
import { createGalaxyApi } from "@galaxyproject/galaxy-api-client";

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
import { GalaxyApi } from "@galaxyproject/galaxy-api-client";
const legacyApi = GalaxyApi(); // Uses current origin
```

### Usage with API Keys and Custom Headers

```typescript
import { createGalaxyApi } from "@galaxyproject/galaxy-api-client";

// Create a client with API key authentication and custom headers
const api = createGalaxyApi({
    baseUrl: "https://usegalaxy.org",
    apiKey: "your-api-key-here",
    headers: {
        Accept: "application/json",
    },
    fetchOptions: {
        credentials: "include", // Include cookies for CORS requests
        cache: "no-cache", // Don't cache responses
    },
});

// Now all requests will include the API key header and custom options
const { data, error } = await api.GET("/api/histories");
```

## Type Safety

This package provides TypeScript types for Galaxy API endpoints and models:

```typescript
import { createGalaxyApi, type HistorySummary, type DatasetEntry } from "@galaxyproject/galaxy-api-client";

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

## Examples

See `src/example.ts` for more complete examples. Here are some common operations:

### Working with Histories

```typescript
import { createGalaxyApi } from "@galaxyproject/galaxy-api-client";

const api = createGalaxyApi({
    baseUrl: "https://usegalaxy.org",
    apiKey: "your-api-key",
});

// List all histories
const { data: histories, error } = await api.GET("/api/histories");

// Get most recently used history
const { data: recent } = await api.GET("/api/histories/most_recently_used");

// Get history details
const { data: history } = await api.GET("/api/histories/{history_id}", {
    params: { path: { history_id: "abc123" } },
});

// Update a history
const { data: updated } = await api.PUT("/api/histories/{history_id}", {
    params: { path: { history_id: "abc123" } },
    body: { name: "My Analysis", annotation: "RNA-seq experiment" },
});
```

### Working with Workflows

```typescript
// List workflows
const { data: workflows } = await api.GET("/api/workflows");

// Get workflow details
const { data: workflow } = await api.GET("/api/workflows/{workflow_id}", {
    params: { path: { workflow_id: "def456" } },
});

// Check invocation status
const { data: invocation } = await api.GET("/api/invocations/{invocation_id}", {
    params: { path: { invocation_id: "ghi789" } },
});
```

### Checking Job Status

```typescript
// Get job details
const { data: job } = await api.GET("/api/jobs/{job_id}", {
    params: { path: { job_id: "jkl012" } },
});

console.log(`Job state: ${job.state}`);
```

## Notes

This package uses a symlink to reference API type definitions from the main Galaxy client while providing a standalone client implementation. This approach was chosen to:

1. Minimize duplication of type definitions
2. Ensure type definitions stay in sync with the main codebase
3. Allow the client to work independently of Galaxy's internal utilities

## Development

To work on this package:

1. Make changes to the API type definitions in the main Galaxy client
2. The type changes will automatically be available in this package via symlinks
3. Synchronize the version with Galaxy:

    ```bash
    # Update the version in package.json from Galaxy's version.py
    npm run sync-version
    ```

4. Build the library for distribution:

    ```bash
    # Install dependencies
    npm install

    # Build the library
    npm run build

    # Watch mode for development
    npm run dev
    ```

### Version Synchronization

This package maintains version parity with Galaxy to indicate API compatibility. The version number in `package.json` is derived from Galaxy's `lib/galaxy/version.py` file but formatted to comply with npm's semver requirements.

**Important:** npm does not allow republishing the same version, even for development versions. When making changes to the client API during development:

1. Manually increment the version before publishing:

    ```bash
    # Example: Update from 25.0.0-dev.0 to 25.0.0-dev.1
    npm version prerelease --preid=dev
    ```

2. Or edit the npm version directly in package.json:
    ```json
    {
        "version": "25.0.0-dev.1"
    }
    ```

There's also a script to automate syncing with the Galaxy version:

```bash
# Using npm script
npm run sync-version
```

The script will:

1. Read the version from Galaxy's `version.py` file
2. Convert it to npm-compatible semver format
3. Update the version in `package.json` if different

Version synchronization should be performed before each release to ensure the client API version accurately reflects the Galaxy API version it supports.

### Testing

The package includes a few vitest tests as a sanity check, but we could do a lot more here:

```bash
# Run tests
npm test

# Run tests with watch mode (during development)
npm run test:watch
```

The tests verify:

- Client creation with default and custom base URLs
- Basic API interaction with proper typing
- Error handling
