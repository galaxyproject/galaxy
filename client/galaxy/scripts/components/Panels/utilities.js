import _ from "underscore";
import _l from "utils/localization";
import { getAppRoot } from "onload";

export function getPanelProps(panelComponent, options = {}) {
    const storedWorkflowMenuEntries = options.stored_workflow_menu_entries || [];
    return {
        side: "left",
        currentPanel: panelComponent,
        currentPanelProperties: {
            appRoot: getAppRoot(),
            toolsTitle: _l("Tools"),
            workflowGlobals: options.workflow_globals,
            toolbox: options.toolbox,
            moduleSections: options.module_sections,
            dataManagers: {
                name: _l("Data Managers"),
                elems: options.data_managers
            },
            workflowsTitle: _l("Workflows"),
            workflowSection: {
                name: _l("Workflows"),
                elems: options.workflows.map(workflow => {
                    return {
                        id: workflow.latest_id,
                        name: workflow.name
                    };
                })
            },
            workflows: [
                {
                    title: _l("All workflows"),
                    href: `${getAppRoot()}workflows/list`,
                    id: "list"
                },
                ...storedWorkflowMenuEntries.map(menuEntry => {
                    return {
                        title: menuEntry["stored_workflow"]["name"],
                        href: `${getAppRoot()}workflows/run?id=${menuEntry["encoded_stored_workflow_id"]}`,
                        id: menuEntry["encoded_stored_workflow_id"]
                    };
                })
            ]
        }
    };
}

// create tool search, tool panel, and tool panel view.
export function getToolSections(toolbox, disabledCaller) {
    return _.map(toolbox, category => {
        return {
            ...category,
            panel_type: getPanelType(category),
            elems: _.map(category.elems, el => {
                el.panel_type = getPanelType(el);
                el.disabled = disabledCaller ? disabledCaller(el) : false;
                return el;
            })
        };
    });
}

export function filterToolSections(layout, results) {
    if (results) {
        return _.filter(
            _.map(layout, category => {
                return {
                    ...category,
                    elems: (filtered => {
                        return _.filter(filtered, (el, i) => {
                            if (el.panel_type == "label") {
                                return filtered[i + 1] && filtered[i + 1].panel_type == "tool";
                            } else {
                                return true;
                            }
                        });
                    })(
                        _.filter(category.elems, el => {
                            if (el.panel_type == "label") {
                                return true;
                            } else {
                                return results.includes(el.id);
                            }
                        })
                    )
                };
            }),
            category => {
                return category.elems.length || (category.panel_type == "tool" && results.includes(category.id));
            }
        );
    } else {
        return layout;
    }
}

export function getPanelType(el) {
    if (el.model_class.endsWith("ToolSection")) {
        return "section";
    }
    if (el.model_class.endsWith("ToolSectionLabel")) {
        return "label";
    }
    return "tool";
}
