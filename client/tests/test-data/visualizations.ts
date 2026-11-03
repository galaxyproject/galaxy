import type { VisualizationSummary } from "@/api/visualizations";

export function getFakeVisualizationSummary(overrides: Partial<VisualizationSummary> = {}): VisualizationSummary {
    return {
        id: "visualization-id",
        title: "Test Visualization",
        type: "nvd3_bar",
        annotation: null,
        create_time: "2026-01-01T00:00:00",
        update_time: "2026-01-02T00:00:00",
        deleted: false,
        importable: false,
        published: false,
        tags: [],
        username: "test-user",
        ...overrides,
    };
}
