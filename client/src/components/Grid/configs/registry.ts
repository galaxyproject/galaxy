import { Config } from "./types";
import { VisualizationsGrid } from "./visualizations";
import { VisualizationsPublishedGrid } from "./visualizationsPublished";

export const registry: Record<string, Config> = {
    visualizations: VisualizationsGrid,
    visualizations_published: VisualizationsPublishedGrid,
};
