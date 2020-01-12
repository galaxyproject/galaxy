import _ from "underscore";
import _l from "utils/localization";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";

export function getPanelProps(panelComponent, options = {}) {
    const Galaxy = getGalaxyInstance();
    const appRoot = getAppRoot();
    const storedWorkflowMenuEntries = options.stored_workflow_menu_entries || [];
    return {
        side: "left",
        currentPanel: panelComponent,
        currentPanelProperties: {
            appRoot: getAppRoot(),
            toolsTitle: _l("Tools"),
            toolbox_in_panel: options.toolbox_in_panel,
            isUser: !!(Galaxy.user && Galaxy.user.id),
            moduleSections: options.module_sections,
            dataManagers: {
                name: _l("Data Managers"),
                elems: options.data_managers,
            },
            workflowsTitle: _l("Workflows"),
            workflows: [
                {
                    title: _l("All workflows"),
                    href: `${appRoot}workflows/list`,
                    id: "list"
                },
                ...storedWorkflowMenuEntries.map(menuEntry => {
                    return {
                        title: menuEntry["stored_workflow"]["name"],
                        href: `${appRoot}workflows/run?id=${menuEntry["encoded_stored_workflow_id"]}`,
                        id: menuEntry["encoded_stored_workflow_id"]
                    };
                })
            ]
        }
    };
}

// create tool search, tool panel, and tool panel view.
export function getToolSections(options) {
    console.log(options);
    return _.map(options.toolbox_in_panel, category => {
        return {
            ...category,
            panel_type: getPanelType(category),
            elems: _.map(category.elems, el => {
                el.panel_type = getPanelType(el);
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
