import { orderBy } from "lodash";

export function filterToolSections(tools, results) {
    let toolsResults = [];
    let toolsResultsSection = [];

    if (hasResults(results)) {
        results = normalizeResults(results);
        toolsResults = tools.map((section) => {
            tools = flattenToolsSection(section);
            toolsResultsSection = mapToolsResults(tools, results);
            toolsResultsSection = sortToolsResults(toolsResultsSection);

            return {
                ...section,
                elems: toolsResultsSection,
            };
        });

        toolsResults = deleteEmptySections(toolsResults, results);
    } else {
        toolsResults = tools;
    }

    return toolsResults
}

export function filterTools(tools, results) {
    let toolsResults = [];
    
    if (hasResults(results)) {
        tools = normalizeTools(tools);
        results = normalizeResults(results);
        toolsResults = mapToolsResults(tools, results);
        toolsResults = sortToolsResults(toolsResults);
    } else {
        toolsResults = tools;
    }

    return toolsResults;
}

function normalizeTools(tools) {
    let normalizedTools = [];

    normalizedTools = hideToolsSection(tools, "Expression Tools");
    normalizedTools = flattenTools(normalizedTools);

    return normalizedTools;
}

function flattenToolsSection(section) {
    let flattenTools = [];

    if (section.elems) {
        section.elems.forEach((elem) => {
            if (!elem.text) {
                flattenTools.push(elem);
            }
        });
    } else if (!section.text) {
        flattenTools.push(section);
    }

    return flattenTools;
}

function normalizeResults(results) {
    let normalizedResults = [];

    if (hasResults(results)) {
        results.forEach((result) => {
            normalizedResults.push(result);
        });
    } else {
        normalizedResults = results;
    }

    return normalizedResults;
}

function mapToolsResults(tools, results) {
    let toolsResults = [];
    let apiSort = {};

    toolsResults = tools
        //TODO what was the purpose of the following clause? !el.text
        .filter(tool => /*!el.text && */results.includes(tool.id))
        .map(tool => {
            apiSort = {apiSort: results.indexOf(tool.id)};
            Object.assign(tool, apiSort);
            return tool;
        });

    return toolsResults;
}
function sortToolsResults(toolsResults) {
    toolsResults = orderBy(toolsResults, ['apiSort'], ['asc']);

    return toolsResults;
}

function deleteEmptySections(tools, results) {
    tools = tools
        .filter((section) => {
            const isSection = section.elems && section.elems.length > 0;
            const isMatchedTool = !section.text && results.includes(section.id);
            return isSection || isMatchedTool;
        })
        .sort((sect1, sect2) => {
            if (sect1.elems.length == 0 || sect2.elems.length == 0) {
                return 0;
            }
            return results.indexOf(sect1.elems[0].id) - results.indexOf(sect2.elems[0].id);
        });
    
    return tools;
}

function hideToolsSection(tools, sectionName) {
    return tools.filter((section) => section.name !== sectionName);
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
