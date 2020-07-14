
import { getAppRoot } from "onload";

export function toolsExtracted(tools) {
    function extractSections(acc, section) {
        function extractTools(_acc, tool) {
            return tool.name
                ? [
                        ..._acc,
                        {
                            id: tool.id,
                            name: tool.name,
                            section: section.name,
                            description: tool.description,
                            url: getAppRoot() + String(tool.link).substring(1),
                            version: tool.version,
                            help: tool.help,
                        },
                    ]
                : _acc;
        }
        if ("elems" in section) {
            return acc.concat(section.elems.reduce(extractTools, []));
        }
        return acc;
    }
    return tools
        .reduce(extractSections, [])
        .map((a) => [Math.random(), a])
        .sort((a, b) => a[0] - b[0])
        .map((a) => a[1]);
}