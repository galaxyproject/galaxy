import yaml from "yaml";
import type { Plugin } from "vite";

export function yamlPlugin(): Plugin {
    return {
        name: "vite-plugin-yaml",
        transform(code, id) {
            if (id.endsWith(".yml") || id.endsWith(".yaml")) {
                const data = yaml.parse(code);
                return {
                    code: `export default ${JSON.stringify(data)}`,
                    map: null,
                };
            }
        },
    };
}
