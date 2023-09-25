/**
 * Utilities file for Panel Searches (panel/client search + advanced/backend search)
 * Note: Any mention of "DL" in this file refers to the Demerau-Levenshtein distance algorithm
 */
import { orderBy } from "lodash";
import levenshteinDistance from "utils/levenshtein";
import { localize } from "utils/localization";

const TOOL_ID_KEYS = ["id", "tool_id"];
const TOOLS_RESULTS_SORT_LABEL = "apiSort";
const TOOLS_RESULTS_SECTIONS_HIDE = ["Expression Tools"];
const STRING_REPLACEMENTS = [" ", "-", "(", ")", "'", ":", `"`];
const MINIMUM_DL_LENGTH = 5; // for Demerau-Levenshtein distance
const UNSECTIONED_SECTION = {
    // to return a section for unsectioned tools
    model_class: "ToolSection",
    id: "unsectioned",
    name: localize("Unsectioned Tools"),
    description: localize("Tools that don't appear under any section in the unsearched panel"),
};

/** Converts filters into tool search backend whoosh query.
 * @param {Object} filterSettings e.g.: {"name": "Tool Name", "section": "Collection", ...}
 * @param {String} panelView (if not `default`, does ontology search at backend)
 * @param {Array} toolbox (to find ontology id if given ontology name)
 * @returns parsed Whoosh `query`
 * @example
 *      createWhooshQuery(filterSettings, 'ontology:edam_topics', toolbox)
 *      return query = "(name:(skew) name_exact:(skew) description:(skew)) AND (edam_topics:(topic_0797) AND )"
 */
export function createWhooshQuery(filterSettings) {
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
        if (key === "ontology" && filterValue.includes("operation")) {
            query += "edam_operations:(" + filterValue + ") AND ";
        } else if (key === "ontology" && filterValue.includes("topic")) {
            query += "edam_topics:(" + filterValue + ") AND ";
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

// Given toolbox and search results, returns filtered tool results (by id)
export function filterTools(toolsById, results) {
    const filteredTools = {};
    for (const id of results) {
        const localTool = toolsById[id];
        if (localTool !== undefined) {
            filteredTools[id] = localTool;
        }
    }
    return filteredTools;
}

/**
 * Given toolbox, keys to sort/search results by and a search query,
 * Does a direct string.match() comparison to find results,
 * If that produces nothing, runs DL distance alg to allow misspells
 *
 * @param {Array} tools - toolbox
 * @param {Object} keys - keys to sort and search results by
 * @param {String} query - a search query
 * @param {String} panelView - panel view, to find section_id for each tool
 * @param {Object} currentPanel - current ToolPanel with { section_id: { tools: [tool ids] }, ... }
 * @param {Boolean} usesDL - Optional: used for recursive call with DL if no string.match()
 * @returns an object containing
 * - results: array of tool ids that match the query
 * - resultPanel: a ToolPanel with only the results for the current panelView
 * - closestTerm: Optional: closest matching term for DL (in case no match with query)
 *
 * all sorted by order of keys that are being searched (+ closest matching term if DL)
 */
export function searchToolsByKeys(tools, keys, query, panelView = "default", currentPanel, usesDL = false) {
    const matchedTools = [];
    let closestTerm = null;
    // if user's query = "id:1234" or "tool_id:1234", only search for id
    const id = processForId(query, TOOL_ID_KEYS);
    if (id) {
        query = id;
        keys = { id: 1 };
    }
    const queryValue = sanitizeString(query.trim().toLowerCase(), STRING_REPLACEMENTS);
    for (const tool of tools) {
        for (const key of Object.keys(keys)) {
            if (tool[key] || key === "combined") {
                let actualValue = "";
                // key = "combined" is a special case for searching name + description
                if (key === "combined") {
                    actualValue = (tool.name + tool.description).trim().toLowerCase();
                } else {
                    actualValue = tool[key].trim().toLowerCase();
                }

                // get all (space separated) words in actualValue for tool (for DL)
                const actualValueWords = actualValue.split(" ");
                actualValue = sanitizeString(actualValue, STRING_REPLACEMENTS);

                // do we care for exact matches && is it an exact match ?
                let order = keys.exact && actualValue === queryValue ? keys.exact : keys[key];
                // do we care for startsWith && does it actualValue start with query ?
                order =
                    keys.startsWith && order !== keys.exact && key === "name" && actualValue.startsWith(queryValue)
                        ? keys.startsWith
                        : order;

                if (!usesDL && actualValue.match(queryValue)) {
                    // if string.match() returns true, matching tool found
                    matchedTools.push({ id: tool.id, sections: getPanelSectionsForTool(tool, panelView), order });
                    break;
                } else if (usesDL) {
                    // if string.match() returns false, try DL distance once to see if there is a closestSubstring
                    let substring = null;
                    if ((key == "name" || key == "description") && queryValue.length >= MINIMUM_DL_LENGTH) {
                        substring = closestSubstring(queryValue, actualValue);
                    }
                    // there is a closestSubstring: matching tool found
                    if (substring) {
                        // get the closest matching term for substring
                        const foundTerm = matchingTerm(actualValueWords, substring);
                        if (foundTerm && (!closestTerm || (closestTerm && foundTerm.length < closestTerm.length))) {
                            closestTerm = foundTerm;
                        }
                        matchedTools.push({
                            id: tool.id,
                            sections: getPanelSectionsForTool(tool, panelView),
                            order,
                            closestTerm,
                        });
                        break;
                    }
                }
            }
        }
    }
    // no results with string.match(): recursive call with usesDL
    if (!id && !usesDL && matchedTools.length == 0) {
        return searchToolsByKeys(tools, keys, query, panelView, currentPanel, true);
    }
    const { idResults, resultPanel } = createSortedResultObject(matchedTools, currentPanel);
    return { results: idResults, resultPanel: resultPanel, closestTerm: closestTerm };
}

/**
 * Orders the matchedTools by order of keys that are being searched, and creates a resultPanel
 * @param {Object} matchedTools containing { id: tool id, sections: [section ids], order: order }
 * @param {Object} currentPanel current ToolPanel for current view
 * @returns an object containing
 * - idResults: array of tool ids that match the query
 * - resultPanel: a ToolPanel with only the results
 */
function createSortedResultObject(matchedTools, currentPanel) {
    const idResults = [];
    // creating a sectioned results object ({section_id: [tool ids], ...}), keeping
    // track of the best version of each tool, and also sorting by indexed order of keys
    const resultPanel = orderBy(matchedTools, ["order"], ["desc"]).reduce((acc, tool) => {
        // we either found specific section(s) for tool, or we need to search all sections
        const sections = tool.sections.length !== 0 ? tool.sections : Object.keys(currentPanel);
        for (const section of sections) {
            let toolAdded = false;
            const existingPanelItem = currentPanel[section];
            if (existingPanelItem) {
                if (existingPanelItem.tools && existingPanelItem.tools.includes(tool.id)) {
                    // it has tools so is a section, and it has the tool we're looking for

                    // if we haven't seen this section yet, create it in the resultPanel
                    if (!acc[section]) {
                        acc[section] = { ...existingPanelItem };
                        acc[section].tools = [];
                    }
                    acc[section].tools.push(tool.id);
                    toolAdded = true;
                } else if (isToolObject(existingPanelItem) && existingPanelItem.id === tool.id) {
                    // it is a tool, and it is the tool we're looking for

                    // put in it the "Unsectioned Tools" section (if it doesn't exist, create it)
                    const unsectionedId = UNSECTIONED_SECTION.id;
                    if (!acc[unsectionedId]) {
                        acc[unsectionedId] = { ...UNSECTIONED_SECTION };
                        acc[unsectionedId].tools = [];
                    }
                    acc[unsectionedId].tools.push(tool.id);
                    toolAdded = true;
                }
                if (toolAdded && !idResults.includes(tool.id)) {
                    idResults.push(tool.id);
                }
            }
        }
        return acc;
    }, {});
    return { idResults, resultPanel };
}

/**
 * Gets the section(s) a tool belongs to for a given panelView.
 * Unless view=`default`, all other views must be of format `class:view_type`,
 * where `Tool` object has a `view_name` key containing an array of section ids.
 * e.g.: view = `ontology:edam_operations` => `Tool.edam_operations = [section ids]`.
 *
 * Therefore, this would not handle the case where view = `ontology:edam_merged`, since
 * Tool.edam_merged is not a valid key, and we would just return `[uncategorized]`.
 *
 * Just prevents looking through whole panel to find section id for tool,
 * we still end up doing that (in `createSortedResultObject`) in case we return [] here
 * @param {Tool} tool
 * @param {String} panelView
 * @returns Array of section ids
 */
function getPanelSectionsForTool(tool, panelView) {
    if (panelView === "default" && tool.panel_section_id) {
        if (tool.panel_section_id.startsWith("tool_")) {
            return [tool.panel_section_id.split("tool_")[1]];
        } else {
            return [tool.panel_section_id];
        }
    } else if (panelView !== "default") {
        const sectionType = panelView.split(":")[1]; // e.g.: edam_operations
        if (tool[sectionType] && tool[sectionType].length !== 0) {
            return tool[sectionType];
        } else {
            return ["uncategorized"];
        }
    }
    return [];
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

export function isToolObject(tool) {
    // toolbox overhaul with typing will simplify this dramatically...
    // Right now, our shorthand is that tools have no 'text', and don't match
    // the model_class of the section/label.
    if (
        !tool.text &&
        tool.model_class !== "ToolSectionLabel" &&
        tool.model_class !== "ToolSection" &&
        tool.tools === undefined
    ) {
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

/**
 * If the query is of the form "id:1234" (or "tool_id:1234"), return the id.
 * Otherwise, return null.
 * @param {String} query - the raw query
 * @param {Array} keys - Optional: keys to check for (default: ["id"])
 * @returns id or null
 */
function processForId(query, keys = ["id"]) {
    for (const key of keys) {
        if (query.includes(`${key}:`)) {
            return query.split(`${key}:`)[1].trim();
        }
    }
    return null;
}
