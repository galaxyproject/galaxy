// Example usage of the Galaxy API client
import { createGalaxyApi } from "./index";

// Create a client
const api = createGalaxyApi("https://usegalaxy.org");

// Example function to get a list of tools
async function getTools() {
    const { data, error } = await api.GET("/api/tools");

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
    const { data, error } = await api.GET("/api/tools/{tool_id}", {
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

export { getTools, getToolById };
