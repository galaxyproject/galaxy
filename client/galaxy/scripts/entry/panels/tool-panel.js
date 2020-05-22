import $ from "jquery";
import Backbone from "backbone";
import UploadModal from "components/Upload/UploadModal";
import _l from "utils/localization";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";
import Vue from "vue";
import ToolBox from "../../components/Panels/ToolBox";
import SidePanel from "../../components/Panels/SidePanel";
import { mountVueComponent } from "../../utils/mountVueComponent";

const ToolPanel = Backbone.View.extend({
    initialize: function () {
        const Galaxy = getGalaxyInstance();
        const appRoot = getAppRoot();

        // add upload modal
        const modalInstance = Vue.extend(UploadModal);
        const propsData = {
            uploadPath: Galaxy.config.nginx_upload_path || `${appRoot}api/tools`,
            chunkUploadSize: Galaxy.config.chunk_upload_size,
            ftpUploadSite: Galaxy.config.ftp_upload_site,
            defaultGenome: Galaxy.config.default_genome,
            defaultExtension: Galaxy.config.default_extension,
        };
        const vm = document.createElement("div");
        $("body").append(vm);
        const upload = new modalInstance({
            propsData: propsData,
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
        return mountVueComponent(SidePanel)(
            {
                side: "left",
                currentPanel: ToolBox,
                currentPanelProperties: Galaxy.config,
            },
            el
        );
    },

    getVueComponent: function () {
        const Galaxy = getGalaxyInstance();
        const SidePanelClass = Vue.extend(SidePanel);
        return new SidePanelClass({
            propsData: {
                side: "left",
                currentPanel: ToolBox,
                currentPanelProperties: Galaxy.config,
            },
        });
    },

    toString: function () {
        return "toolPanel";
    },
});

export default ToolPanel;
