import { orderBy } from "lodash";

const TOOLS_RESULTS_SORT_LABEL = "apiSort";
const TOOLS_RESULTS_SECTIONS_HIDE = ["Expression Tools"];

export function filterTools(tools, results) {
    let toolsResults = [];

    if (hasResults(results)) {
        tools = normalizeTools(tools);
        toolsResults = mapToolsResults(tools, results);
        toolsResults = sortToolsResults(toolsResults);
    } else {
        toolsResults = tools;
    }

    return toolsResults;
}

export function filterToolSections(tools, results) {
    let toolsResults = [];
    let toolsResultsSection = [];

    if (hasResults(results)) {
        toolsResults = tools.map((section) => {
            tools = flattenToolsSection(section);
            toolsResultsSection = mapToolsResults(tools, results);
            toolsResultsSection = sortToolsResults(toolsResultsSection);

            return {
                ...section,
                elems: toolsResultsSection,
            };
        });
        toolsResults = deleteEmptyToolsSections(toolsResults, results);
    } else {
        toolsResults = tools;
    }

    return toolsResults;
}

function normalizeTools(tools) {
    tools = hideToolsSection(tools);
    tools = flattenTools(tools);

    return tools;
}

function flattenToolsSection(section) {
    const flattenTools = [];

    if (section.elems) {
        section.elems.forEach((tool) => {
            if (!tool.text) {
                flattenTools.push(tool);
            }
        });
    } else if (!section.text) {
        flattenTools.push(section);
    }

    return flattenTools;
}

function mapToolsResults(tools, results) {
    const toolsResults = tools
        .filter((tool) => !tool.text && results.includes(tool.id))
        .map((tool) => {
            Object.assign(tool, setSort(tool, results));
            return tool;
        });

    return toolsResults;
}

function setSort(tool, results) {
    return { [TOOLS_RESULTS_SORT_LABEL]: results.indexOf(tool.id) };
}

function sortToolsResults(toolsResults) {
    return orderBy(toolsResults, [TOOLS_RESULTS_SORT_LABEL], ["asc"]);
}

function deleteEmptyToolsSections(tools, results) {
    let isSection = false;
    let isMatchedTool = false;

    tools = tools
        .filter((section) => {
            isSection = section.elems && section.elems.length > 0;
            isMatchedTool = !section.text && results.includes(section.id);
            return isSection || isMatchedTool;
        })
        .sort((sectionPrevious, sectionCurrent) => {
            if (sectionPrevious.elems.length == 0 || sectionCurrent.elems.length == 0) {
                return 0;
            }
            return results.indexOf(sectionPrevious.elems[0].id) - results.indexOf(sectionCurrent.elems[0].id);
        });

    return tools;
}

function hideToolsSection(tools) {
    return tools.filter((section) => !TOOLS_RESULTS_SECTIONS_HIDE.includes(section.name));
}

function flattenTools(tools) {
    let normalizedTools = [];

    tools.forEach((section) => {
        normalizedTools = normalizedTools.concat(flattenToolsSection(section));
    });

    return normalizedTools;
}

function hasResults(results) {
    return Array.isArray(results) && results.length > 0;
}
