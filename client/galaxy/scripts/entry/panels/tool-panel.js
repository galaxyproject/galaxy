import Backbone from "backbone";
import Upload from "mvc/upload/upload-view";
import _l from "utils/localization";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";
import Vue from "vue";
import ToolBox from "../../components/Panels/ToolBox.vue";
import SidePanel from "../../components/Panels/SidePanel.vue";
import { mountVueComponent } from "../../utils/mountVueComponent";

const ToolPanel = Backbone.View.extend({
    initialize: function() {
        const Galaxy = getGalaxyInstance();
        const appRoot = getAppRoot();

        // add uploader button to Galaxy object
        Galaxy.upload = new Upload({
            upload_path: Galaxy.config.nginx_upload_path || `${appRoot}api/tools`,
            chunk_upload_size: Galaxy.config.chunk_upload_size,
            ftp_upload_site: Galaxy.config.ftp_upload_site,
            default_genome: Galaxy.config.default_genome,
            default_extension: Galaxy.config.default_extension
        });

        // components for panel definition
        this.model = new Backbone.Model({
            title: _l("Tools")
        });
    },

    isVueWrapper: true,

    mountVueComponent: function(el) {
        const Galaxy = getGalaxyInstance();
        return mountVueComponent(SidePanel)({
            side: "left",
            currentPanel: ToolBox,
            currentPanelProperties: Galaxy.config
        }, el);
    },

    getVueComponent: function() {
        const Galaxy = getGalaxyInstance();
        const SidePanelClass = Vue.extend(SidePanel);
        return new SidePanelClass({
            propsData: {
                side: "left",
                currentPanel: ToolBox,
                currentPanelProperties: Galaxy.config
            }
        });
    },

    toString: function() {
        return "toolPanel";
    }
});

export default ToolPanel;
