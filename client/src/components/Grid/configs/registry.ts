import { Config } from "./types";
import { VisualizationsGrid } from "./visualizations";

export const registry: Record<string, Config> = {
    visualizations: VisualizationsGrid,
};
