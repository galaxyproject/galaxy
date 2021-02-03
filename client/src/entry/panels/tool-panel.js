import Backbone from "backbone";
import _l from "utils/localization";
import { getGalaxyInstance } from "app";
import ToolBox from "../../components/Panels/ToolBox";
import SidePanel from "../../components/Panels/SidePanel";
import { mountVueComponent } from "../../utils/mountVueComponent";

const ToolPanel = Backbone.View.extend({
    initialize: function () {
        // components for panel definition
        this.model = new Backbone.Model({
            title: _l("Tools"),
        });
    },

    isVueWrapper: true,

    mountVueComponent: function (el) {
        const Galaxy = getGalaxyInstance();
        return (this.component = mountVueComponent(SidePanel)(
            {
                side: "left",
                currentPanel: ToolBox,
                currentPanelProperties: {
                    storedWorkflowMenuEntries: Galaxy.config.stored_workflow_menu_entries,
                    toolbox: Galaxy.config.toolbox,
                },
            },
            el
        ));
    },

    toString: function () {
        return "toolPanel";
    },
});

export default ToolPanel;
