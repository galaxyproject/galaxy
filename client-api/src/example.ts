// Example usage of the Galaxy API client
import { createGalaxyApi } from "./index";

//
// Basic usage - just provide a base URL
//
const basicApi = createGalaxyApi("https://usegalaxy.org");

//
// Advanced usage - with API key authentication and custom headers
//
const authenticatedApi = createGalaxyApi({
    baseUrl: "https://usegalaxy.org",
    apiKey: "your-api-key-here",
    headers: {
        Accept: "application/json",
        "User-Agent": "GalaxyClientApp/1.0",
    },
});

//
// Example with request options (timeouts, credentials, etc.)
//
const apiWithOptions = createGalaxyApi({
    baseUrl: "https://usegalaxy.org",
    fetchOptions: {
        credentials: "include", // Include cookies for CORS requests
        cache: "no-cache", // Don't cache responses
        timeout: 30000, // 30 second timeout
    },
});

// Example function to get a list of tools
async function getTools() {
    // Using the basic API
    const { data, error } = await basicApi.GET("/api/tools");

    if (error) {
        console.error("Error fetching tools:", error);
        return [];
    }

    // Log tool count
    console.log(`Found ${data.length} tools`);

    // Group tools by section
    const sections: Record<string, any[]> = {};
    for (const tool of data) {
        const section = tool.panel_section_name || "Ungrouped";
        if (!sections[section]) sections[section] = [];
        sections[section].push(tool);
    }

    // Print summary
    Object.keys(sections).forEach((section) => {
        console.log(`${section}: ${sections[section].length} tools`);
    });

    return data;
}

// Example function to get a specific tool by ID
async function getToolById(id: string) {
    // Using the authenticated API
    const { data, error } = await authenticatedApi.GET("/api/tools/{tool_id}", {
        params: {
            path: {
                tool_id: id,
            },
        },
    });

    if (error || !data) {
        console.error("Error fetching tool:", error);
        return null;
    }

    return data;
}

// Example function to create a dataset in a history
async function createDataset(historyId: string, name: string, content: string) {
    // Using the API with custom options
    const { data, error } = await apiWithOptions.POST("/api/histories/{history_id}/contents", {
        params: {
            path: {
                history_id: historyId,
            },
        },
        body: {
            name,
            content,
            type: "file",
        },
    });

    if (error) {
        console.error("Error creating dataset:", error);
        return null;
    }

    return data;
}

export { getTools, getToolById, createDataset };
