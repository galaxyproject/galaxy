/**
 * Utilities file for Panel Searches (panel/client search + advanced/backend search)
 * Note: Any mention of "DL" in this file refers to the Demerau-Levenshtein distance algorithm
 */
import { orderBy } from "lodash";

import {
    type FilterSettings as ToolFilters,
    type Tool,
    type ToolSection,
    type ToolSectionLabel,
} from "@/stores/toolStore";
import levenshteinDistance from "@/utils/levenshtein";

const TOOL_ID_KEYS = ["id", "tool_id"];
const STRING_REPLACEMENTS: string[] = [" ", "-", "\\(", "\\)", "'", ":", `"`];
const MINIMUM_DL_LENGTH = 5; // for Demerau-Levenshtein distance
const MINIMUM_WORD_MATCH = 2; // for word match
const UNSECTIONED_SECTION = {
    // to return a section for unsectioned tools
    model_class: "ToolSection",
    id: "unsectioned",
    name: "Unsectioned Tools",
    description: "Tools that don't appear under any section in the unsearched panel",
};
const VALID_SECTION_TYPES = ["edam_operations", "edam_topics"]; // other than `default`

/** These are keys used to order/sort results in `ToolSearch`.
 * The value for each is the sort order, higher number = higher rank.
 * Must include some `Tool` properties (like name, description, id etc.)
 * to check against query, and any other keys below are special, used for
 * specific cases (like `combined` for name+description).
 */
export interface ToolSearchKeys {
    [key: string | keyof Tool]: number | undefined;
    /** property has exact match with query */
    exact?: number;
    /** property starts with query */
    startsWith?: number;
    /** query contains matches `Tool.name + Tool.description` */
    combined?: number;
    /** property matches   */
    wordMatch?: number;
}

interface SearchMatch {
    id: string;
    sections: (string | undefined)[];
    order: number;
}

/** Returns icon for tool panel `view_type` */
export const types_to_icons = {
    default: "undo",
    generic: "filter",
    ontology: "sitemap",
    activity: "project-diagram",
    publication: "newspaper",
    training: "graduation-cap",
};

// Converts filterSettings { key: value } to query = "key:value"
export function createWorkflowQuery(filterSettings: Record<string, string | boolean>) {
    let query = "";
    query = Object.entries(filterSettings)
        .filter(([, value]) => value)
        .map(([filter, value]) => {
            if (value === true) {
                return `is:${filter}`;
            }
            return `${filter}:${value}`;
        })
        .join(" ");
    if (Object.keys(filterSettings).length == 1 && filterSettings.name) {
        return filterSettings.name as string;
    }
    return query;
}

/** Converts filters into tool search backend whoosh query.
 * @param filterSettings e.g.: {"name": "Tool Name", "section": "Collection", ...}
 * @returns parsed Whoosh `query`
 * @example
 *      createWhooshQuery(filterSettings = {"name": "skew", "ontology": "topic_0797"})
 *      return query = "(name:(skew) name_exact:(skew) description:(skew)) AND (edam_topics:(topic_0797) AND )"
 */
export function createWhooshQuery(filterSettings: ToolFilters) {
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
        if (filterValue) {
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
    }
    query += ")";
    return query;
}

// Determines width given the root and draggable element, smallest and largest size and the current position
export function determineWidth(
    rectRoot: { left: number; right: number },
    rectDraggable: { left: number },
    minWidth: number,
    maxWidth: number,
    direction: string,
    positionX: number
) {
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

/**
 * @param toolsById - all tools, keyed by id
 * @param results - list of result tool ids
 * @returns filtered tool results (by id)
 */
export function filterTools(toolsById: Record<string, Tool>, results: string[]) {
    const filteredTools: Record<string, Tool> = {};
    for (const id of results) {
        const localTool = toolsById[id];
        if (localTool !== undefined) {
            filteredTools[id] = localTool;
        }
    }
    return filteredTools;
}

/** Returns a `toolsById` object containing tools that meet required conditions
 * based on params.
 * @param toolsById - object of tools, keyed by id
 * @param isWorkflowPanel - whether or not the ToolPanel is in Workflow Editor
 * @param excludedSectionIds - ids for sections whose tools will be excluded
 */
export function getValidToolsInCurrentView(
    toolsById: Record<string, Tool>,
    isWorkflowPanel = false,
    excludedSectionIds: string[] = []
) {
    const addedToolTexts: string[] = [];
    const toolEntries = Object.entries(toolsById).filter(([, tool]) => {
        // filter out duplicate tools (different ids, same exact name+description)
        // related ticket: https://github.com/galaxyproject/galaxy/issues/16145
        const toolText = tool.name + tool.description;
        if (addedToolTexts.includes(toolText)) {
            return false;
        } else {
            addedToolTexts.push(toolText);
        }
        // filter on non-hidden, non-disabled, and workflow compatibile (based on props.workflow)
        return (
            !tool.hidden &&
            tool.disabled !== true &&
            !(isWorkflowPanel && !tool.is_workflow_compatible) &&
            !excludedSectionIds.includes(tool.panel_section_id || "")
        );
    });
    return Object.fromEntries(toolEntries);
}

/** Looks in each section of `currentPanel` and filters `section.tools` on `validToolIdsInCurrentView` */
export function getValidToolsInEachSection(
    validToolIdsInCurrentView: string[],
    currentPanel: Record<string, Tool | ToolSection>
) {
    return Object.entries(currentPanel).map(([id, section]) => {
        const validatedSection = { ...section } as ToolSection;
        if (validatedSection.tools && Array.isArray(validatedSection.tools)) {
            // filter on valid tools and panel labels in this section
            validatedSection.tools = validatedSection.tools.filter((toolId) => {
                if (typeof toolId === "string" && validToolIdsInCurrentView.includes(toolId)) {
                    return true;
                } else if (typeof toolId !== "string") {
                    // is a special case where there is a label within a section
                    return true;
                }
            });
        }
        return [id, validatedSection];
    });
}

/**
 * @param items - `[id, PanelItem]` entries (from the `currentPanel` object)
 * @param validToolIdsInCurrentView - tool ids that are valid in current view
 * @param excludedSectionIds - any section ids to exclude
 * @returns a `currentPanel` object containing sections/tools/labels that meet required conditions
 */
export function getValidPanelItems(
    items: (string | ToolSection)[][],
    validToolIdsInCurrentView: string[],
    excludedSectionIds: string[] = []
) {
    const validEntries = items.filter(([id, item]) => {
        id = id as string;
        item = item as Tool | ToolSection;
        if (isToolObject(item as Tool) && validToolIdsInCurrentView.includes(id)) {
            // is a `Tool` and is in `localToolsById`
            return true;
        } else if (item.tools === undefined) {
            // is neither a `Tool` nor a `ToolSection`, maybe a `ToolSectionLabel`
            return true;
        } else if (item.tools && item.tools.length > 0 && !excludedSectionIds.includes(id)) {
            // is a `ToolSection` with tools; is not an excluded section
            return true;
        } else {
            return false;
        }
    });
    return Object.fromEntries(validEntries);
}

/**
 * Given toolbox, keys to sort/search results by and a search query,
 * Does a direct string.match() comparison to find results,
 * If that produces nothing, runs DL distance alg to allow misspells
 *
 * @param tools - toolbox
 * @param keys - keys to sort and search results by
 * @param query - a search query
 * @param panelView - panel view, to find section_id for each tool
 * @param currentPanel - current ToolPanel with { section_id: { tools: [tool ids] }, ... }
 * @param usesDL - Optional: used for recursive call with DL if no string.match()
 * @returns an object containing
 * - results: array of tool ids that match the query
 * - resultPanel: a ToolPanel with only the results for the current panelView
 * - closestTerm: Optional: closest matching term for DL (in case no match with query)
 *
 * all sorted by order of keys that are being searched (+ closest matching term if DL)
 */
export function searchToolsByKeys(
    tools: Tool[],
    keys: ToolSearchKeys,
    query: string,
    panelView = "default",
    currentPanel: Record<string, Tool | ToolSection>,
    usesDL = false
): {
    results: string[];
    resultPanel: Record<string, Tool | ToolSection>;
    closestTerm: string | null;
} {
    const matchedTools: SearchMatch[] = [];
    let closestTerm = null;
    // if user's query = "id:1234" or "tool_id:1234", only search for id
    const id = processForId(query, TOOL_ID_KEYS);
    if (id) {
        query = id;
        keys = { id: 1 };
    }

    const queryWords = query.trim().toLowerCase().split(" ");
    const queryValue = sanitizeString(query.trim().toLowerCase(), STRING_REPLACEMENTS);
    for (const tool of tools) {
        for (const key of Object.keys(keys)) {
            if (tool[key as keyof Tool] || key === "combined") {
                let actualValue = "";
                // key = "combined" is a special case for searching name + description
                if (key === "combined") {
                    actualValue = `${tool.name.trim()} ${tool.description.trim()}`.toLowerCase();
                } else {
                    actualValue = (tool[key as keyof Tool] as string)?.trim().toLowerCase();
                }

                // get all (space separated) words in actualValue for tool (for DL)
                const actualValueWords = actualValue.split(" ");
                actualValue = sanitizeString(actualValue, STRING_REPLACEMENTS);

                // do we care for exact matches && is it an exact match ?
                let order =
                    keys.exact !== undefined && actualValue === queryValue
                        ? (keys.exact as number)
                        : (keys[key] as number);
                // do we care for startsWith && does it actualValue start with query ?
                order =
                    keys.startsWith !== undefined &&
                    order !== keys.exact &&
                    key === "name" &&
                    actualValue.startsWith(queryValue)
                        ? keys.startsWith
                        : order;

                const wordMatches = Array.from(new Set(actualValueWords.filter((word) => queryWords.includes(word))));
                if (!usesDL) {
                    if (actualValue.match(queryValue)) {
                        // if string.match() returns true, matching tool found
                        matchedTools.push({ id: tool.id, sections: getPanelSectionsForTool(tool, panelView), order });
                        break;
                    } else if (
                        key === "combined" &&
                        keys.wordMatch !== undefined &&
                        wordMatches.length >= MINIMUM_WORD_MATCH
                    ) {
                        // we are looking at combined name+description, and there are enough word matches
                        matchedTools.push({
                            id: tool.id,
                            sections: getPanelSectionsForTool(tool, panelView),
                            order: keys.wordMatch,
                        });
                        break;
                    }
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
 * @param matchedTools containing { id: tool id, sections: [section ids], order: order }
 * @param currentPanel current ToolPanel for current view
 * @returns an object containing
 * - idResults: array of tool ids that match the query
 * - resultPanel: a ToolPanel with only the results
 */
export function createSortedResultObject(
    matchedTools: SearchMatch[],
    currentPanel: Record<string, Tool | ToolSection>
) {
    const idResults: string[] = [];
    // creating a sectioned results object ({section_id: [tool ids], ...}), keeping
    // track of the best version of each tool, and also sorting by indexed order of keys
    const resultPanel = orderBy(matchedTools, ["order"], ["desc"]).reduce(
        (acc: Record<string, Tool | ToolSection>, match: SearchMatch) => {
            // we either found specific section(s) for tool, or we need to search all sections
            const sections: (string | undefined)[] =
                match.sections.length !== 0 ? match.sections : Object.keys(currentPanel);
            for (const section of sections) {
                let toolAdded = false;
                const existingPanelItem = section ? currentPanel[section] : undefined;
                if (existingPanelItem && section) {
                    if (
                        (existingPanelItem as ToolSection).tools &&
                        (existingPanelItem as ToolSection).tools?.includes(match.id)
                    ) {
                        // it has tools so is a section, and it has the tool we're looking for

                        // if we haven't seen this section yet, create it in the resultPanel
                        let existingSection = acc[section] as ToolSection;
                        if (!existingSection) {
                            existingSection = { ...existingPanelItem };
                            existingSection.tools = [];
                        }
                        existingSection.tools?.push(match.id);
                        acc[section] = existingSection;
                        toolAdded = true;
                    } else if (isToolObject(existingPanelItem as Tool) && existingPanelItem.id === match.id) {
                        // it is a tool, and it is the tool we're looking for

                        // put in it the "Unsectioned Tools" section (if it doesn't exist, create it)
                        const unsectionedId = UNSECTIONED_SECTION.id;
                        let unsectionedSection = acc[unsectionedId] as ToolSection;
                        if (!unsectionedSection) {
                            unsectionedSection = { ...UNSECTIONED_SECTION };
                            unsectionedSection.tools = [];
                        }
                        unsectionedSection.tools?.push(match.id);
                        acc[unsectionedId] = unsectionedSection;
                        toolAdded = true;
                    }
                    if (toolAdded && !idResults.includes(match.id)) {
                        idResults.push(match.id);
                    }
                }
            }
            return acc;
        },
        {}
    );
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
 * @param tool
 * @param panelView
 * @returns Array of section ids
 */
function getPanelSectionsForTool(tool: Tool, panelView: string) {
    if (panelView === "default" && tool.panel_section_id) {
        if (tool.panel_section_id.startsWith("tool_")) {
            return [tool.panel_section_id.split("tool_")[1]];
        } else {
            return [tool.panel_section_id];
        }
    } else if (panelView !== "default") {
        const sectionType = panelView.split(":")[1] as keyof Tool;
        if (
            sectionType &&
            VALID_SECTION_TYPES.includes(sectionType as string) &&
            (tool[sectionType] as string[])?.length !== 0
        ) {
            return tool[sectionType] as string[];
        } else {
            return ["uncategorized"];
        }
    }
    return [];
}

/**
 *
 * @param query
 * @param actualStr
 * @returns substring with smallest DL distance, or null
 */
function closestSubstring(query: string, actualStr: string) {
    // Create max distance
    // Max distance a query and substring can be apart
    const maxDistance = Math.floor(query.length / 5);
    // Create an array of all actualStr substrings that are query length, query length -1, and query length + 1
    const substrings = Array.from({ length: actualStr.length - query.length + maxDistance }, (_, i) =>
        actualStr.substr(i, query.length)
    );
    if (query.length > 1) {
        substrings.push(
            ...Array.from({ length: actualStr.length - query.length + maxDistance + 1 }, (_, i) =>
                actualStr.substr(i, query.length - maxDistance)
            )
        );
    }
    if (actualStr.length > query.length) {
        substrings.push(
            ...Array.from({ length: actualStr.length - query.length }, (_, i) =>
                actualStr.substr(i, query.length + maxDistance)
            )
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

export function isToolObject(tool: Tool | ToolSection | ToolSectionLabel) {
    // toolbox overhaul with typing will simplify this dramatically...
    // Right now, our shorthand is that tools have no 'text', and don't match
    // the model_class of the section/label.
    if (
        !(tool as ToolSectionLabel).text &&
        tool.model_class !== "ToolSectionLabel" &&
        tool.model_class !== "ToolSection" &&
        (tool as ToolSection).tools === undefined
    ) {
        return true;
    }
    return false;
}

// given array and a substring, get the closest matching term for substring
function matchingTerm(termArray: string[], substring: string) {
    const sanitized = sanitizeString(substring);

    for (const i in termArray) {
        const term = termArray[i];
        if (term?.match(sanitized)) {
            return term;
        }
    }
    return null;
}

/**
 *
 * @param value - to be sanitized
 * @param targets - Optional: characters to replace
 * @param substitute - Optional: replacement character
 * @returns sanitized string
 */
function sanitizeString(value: string, targets: string[] = [], substitute = "") {
    let sanitized = value;
    targets.forEach((rep) => {
        sanitized = sanitized.replace(new RegExp(rep, "g"), substitute);
    });

    return sanitized.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * If the query is of the form "id:1234" (or "tool_id:1234"), return the id.
 * Otherwise, return null.
 * @param query - the raw query
 * @param keys - Optional: keys to check for (default: ["id"])
 * @returns id or null
 */
function processForId(query: string, keys = ["id"]) {
    for (const key of keys) {
        if (query.includes(`${key}:`)) {
            return query.split(`${key}:`)[1]?.trim();
        }
    }
    return null;
}
