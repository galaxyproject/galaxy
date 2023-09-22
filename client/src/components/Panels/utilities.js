/**
 * Utilities file for Panel Searches (panel/client search + advanced/backend search)
 */
import { orderBy } from "lodash";
import levenshteinDistance from "utils/levenshtein";

const TOOLS_RESULTS_SORT_LABEL = "apiSort";
const TOOLS_RESULTS_SECTIONS_HIDE = ["Expression Tools"];
const STRING_REPLACEMENTS = [" ", "-", "(", ")", "'", ":"];

// Converts filterSettings { key: value } to query = "key:value"
export function createWorkflowQuery(filterSettings) {
    let query = "";
    query = Object.entries(filterSettings)
        .filter(([filter, value]) => value)
        .map(([filter, value]) => {
            if (value === true) {
                return `is:${filter}`;
            }
            return `${filter}:${value}`;
        })
        .join(" ");
    if (Object.keys(filterSettings).length == 1 && filterSettings.name) {
        return filterSettings.name;
    }
    return query;
}

/** Converts filters into tool search backend whoosh query.
 * @param {Object} filterSettings e.g.: {"name": "Tool Name", "section": "Collection", ...}
 * @param {String} panelView (if not `default`, does ontology search at backend)
 * @param {Array} toolbox (to find ontology id if given ontology name)
 * @returns parsed Whoosh `query`
 * @example
 *      createWhooshQuery(filterSettings, 'ontology:edam_topics', toolbox)
 *      return query = "(name:(skew) name_exact:(skew) description:(skew)) AND (edam_topics:(topic_0797) AND )"
 */
export function createWhooshQuery(filterSettings, panelView, toolbox) {
    let query = "(";
    // add description+name_exact fields = name, to do a combined OrGroup at backend
    const name = filterSettings["name"];
    if (name) {
        query += "name:(" + name + ") ";
        query += "name_exact:(" + name + ") ";
        query += "description:(" + name + ")";
    }
    query += ") AND (";
    for (const [key, filterValue] of Object.entries(filterSettings)) {
        // get ontology keys if view is not default
        if (key === "section" && panelView !== "default") {
            const ontology = toolbox.find(({ name }) => name && name.toLowerCase().match(filterValue.toLowerCase()));
            if (ontology) {
                let ontologyKey = "";
                if (panelView === "ontology:edam_operations") {
                    ontologyKey = "edam_operations";
                } else if (panelView === "ontology:edam_topics") {
                    ontologyKey = "edam_topics";
                }
                query += ontologyKey + ":(" + ontology.id + ") AND ";
            } else {
                query += key + ":(" + filterValue + ") AND ";
            }
        } else if (key == "id") {
            query += "id_exact:(" + filterValue + ") AND ";
        } else if (key != "name") {
            query += key + ":(" + filterValue + ") AND ";
        }
    }
    query += ")";
    return query;
}

// Determines width given the root and draggable element, smallest and largest size and the current position
export function determineWidth(rectRoot, rectDraggable, minWidth, maxWidth, direction, positionX) {
    let newWidth = null;
    if (direction === "right") {
        const offset = rectRoot.left - rectDraggable.left;
        newWidth = rectRoot.right - positionX - offset;
    } else {
        const offset = rectRoot.right - rectDraggable.left;
        newWidth = positionX - rectRoot.left + offset;
    }
    return Math.max(minWidth, Math.min(maxWidth, newWidth));
}

// Given toolbox and search results, returns filtered tool results
export function filterTools(tools, results) {
    let toolsResults = [];
    tools = flattenTools(tools);
    toolsResults = mapToolsResults(tools, results);
    toolsResults = sortToolsResults(toolsResults);
    toolsResults = removeDuplicateResults(toolsResults);
    return toolsResults;
}

// Given toolbox and search results, returns filtered tool results by sections
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

export function hasResults(results) {
    return Array.isArray(results) && results.length > 0;
}

/**
 * Given toolbox, keys to sort/search results by and a search query,
 * Does a direct string.match() comparison to find results,
 * If that produces nothing, runs DL distance alg to allow misspells
 *
 * @param {Array} tools - toolbox
 * @param {Object} keys - keys to sort and search results by
 * @param {String} query - a search query
 * @param {Boolean} usesDL - Optional: used for recursive call with DL if no string.match()
 * @returns tool ids sorted by order of keys that are being searched (+ closest matching term if DL)
 */
export function searchToolsByKeys(tools, keys, query, usesDL = false) {
    let returnedTools = [];
    let closestTerm = null;
    const queryValue = sanitizeString(query.trim().toLowerCase(), STRING_REPLACEMENTS);
    const minimumQueryLength = 5; // for DL
    for (const tool of tools) {
        for (const key of Object.keys(keys)) {
            if (tool[key] || key === "combined") {
                let actualValue = "";
                if (key === "combined") {
                    actualValue = (tool.name + tool.description).trim().toLowerCase();
                } else {
                    actualValue = tool[key].trim().toLowerCase();
                }
                const actualValueWords = actualValue.split(" ");
                actualValue = sanitizeString(actualValue, STRING_REPLACEMENTS);
                // do we care for exact matches && is it an exact match ?
                const order = keys.exact && actualValue === queryValue ? keys.exact : keys[key];
                if (!usesDL && actualValue.match(queryValue)) {
                    returnedTools.push({ id: tool.id, order });
                    break;
                } else if (usesDL) {
                    let substring = null;
                    if ((key == "name" || key == "description") && queryValue.length >= minimumQueryLength) {
                        substring = closestSubstring(queryValue, actualValue);
                    }
                    // there is a closestSubstring: matching tool found
                    if (substring) {
                        // get the closest matching term for substring
                        const foundTerm = matchingTerm(actualValueWords, substring);
                        if (foundTerm && (!closestTerm || (closestTerm && foundTerm.length < closestTerm.length))) {
                            closestTerm = foundTerm;
                        }
                        returnedTools.push({ id: tool.id, order, closestTerm });
                        break;
                    }
                }
            }
        }
    }
    // no results with string.match(): recursive call with usesDL
    if (!usesDL && returnedTools.length == 0) {
        return searchToolsByKeys(tools, keys, query, true);
    }
    // sorting results by indexed order of keys
    returnedTools = orderBy(returnedTools, ["order"], ["desc"]).map((tool) => tool.id);
    return { results: returnedTools, closestTerm: closestTerm };
}

export function flattenTools(tools) {
    let normalizedTools = [];
    tools.forEach((section) => {
        normalizedTools = normalizedTools.concat(flattenToolsSection(section));
    });
    return normalizedTools;
}

export function hideToolsSection(tools) {
    return tools.filter((section) => !TOOLS_RESULTS_SECTIONS_HIDE.includes(section.name));
}

export function removeDisabledTools(tools) {
    return tools.filter((section) => {
        if (section.model_class === "ToolSectionLabel") {
            return true;
        } else if (!section.elems && section.disabled) {
            return false;
        } else if (section.elems) {
            section.elems = section.elems.filter((el) => !el.disabled);
            if (!section.elems.length) {
                return false;
            }
        }
        return true;
    });
}

/**
 *
 * @param {String} query
 * @param {String} actualStr
 * @returns substring with smallest DL distance, or null
 */
function closestSubstring(query, actualStr) {
    // Max distance a query and substring can be apart
    const maxDistance = 1;
    // Create an array of all actualStr substrings that are query length, query length -1, and query length + 1
    const substrings = Array.from({ length: actualStr.length - query.length + 1 }, (_, i) =>
        actualStr.substr(i, query.length)
    );
    if (query.length > 1) {
        substrings.push(
            ...Array.from({ length: actualStr.length - query.length + 2 }, (_, i) =>
                actualStr.substr(i, query.length - 1)
            )
        );
    }
    if (actualStr.length > query.length) {
        substrings.push(
            ...Array.from({ length: actualStr.length - query.length }, (_, i) => actualStr.substr(i, query.length + 1))
        );
    }
    // check to see if any substrings have a levenshtein distance less than the max distance
    for (const substring of substrings) {
        if (levenshteinDistance(query, substring, true) <= maxDistance) {
            return substring;
        }
    }
    return null;
}

function isToolObject(tool) {
    // toolbox overhaul with typing will simplify this dramatically...
    // Right now, our shorthand is that tools have no 'text', and don't match
    // the model_class of the section/label.
    if (!tool.text && tool.model_class !== "ToolSectionLabel" && tool.model_class !== "ToolSection") {
        return true;
    }
    return false;
}

// given array and a substring, get the closest matching term for substring
function matchingTerm(termArray, substring) {
    const sanitized = sanitizeString(substring);

    for (const i in termArray) {
        const term = termArray[i];
        if (term.match(sanitized)) {
            return term;
        }
    }
    return null;
}

/**
 *
 * @param {String} value - to be sanitized
 * @param {Array} targets - Optional: characters to replace
 * @param {String} substitute - Optional: replacement character
 * @returns sanitized string
 */
function sanitizeString(value, targets = [], substitute = "") {
    let sanitized = value;
    targets.forEach((rep) => {
        sanitized = sanitized.replaceAll(rep, substitute);
    });

    return sanitized.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function flattenToolsSection(section) {
    const flattenTools = [];
    if (section.elems) {
        section.elems.forEach((tool) => {
            if (isToolObject(tool)) {
                flattenTools.push(tool);
            }
        });
    } else if (isToolObject(section)) {
        // This might be a top-level section-less tool and not actually a
        // section.
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

function removeDuplicateResults(results) {
    const uniqueTools = [];
    return results.filter((tool) => {
        if (!uniqueTools.includes(tool.id)) {
            uniqueTools.push(tool.id);
            return true;
        } else {
            return false;
        }
    });
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
