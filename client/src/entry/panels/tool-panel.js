import $ from "jquery";
import Backbone from "backbone";
import { UploadModal, initializeUploadDefaults } from "components/Upload";
import _l from "utils/localization";
import { getGalaxyInstance } from "app";
import Vue from "vue";
import ToolBox from "../../components/Panels/ToolBox";
import SidePanel from "../../components/Panels/SidePanel";
import { mountVueComponent } from "../../utils/mountVueComponent";
import store from "../../store";

const ToolPanel = Backbone.View.extend({
    initialize: function () {
        const Galaxy = getGalaxyInstance();

        // add upload modal
        const modalInstance = Vue.extend(UploadModal);
        const propsData = initializeUploadDefaults();
        const vm = document.createElement("div");
        $("body").append(vm);
        const upload = new modalInstance({
            propsData: propsData,
            store,
        }).$mount(vm);

        // attach upload entrypoint to Galaxy object
        Galaxy.upload = upload;

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
