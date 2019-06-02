<template>
    <b-modal v-model="modalShow" title="BootstrapVue">
        <b-form-group
            label="Target Section:"
            description="Choose an existing section in your tool panel to contain the installed tools (optional)."
        >
            <b-form-input list="sectionSelect" v-model="toolSection" />
            <datalist id="sectionSelect">
                <option v-for="section in toolSections">{{ section }}</option>
            </datalist>
        </b-form-group>
        <b-form-group label="Tool Configuration:" description="Choose a tool configuration.">
            <div class="ui-select">
                <b-form-select :options="toolConfigs" v-model="toolConfig" />
            </div>
        </b-form-group>
    </b-modal>
</template>
<script>
import { getGalaxyInstance } from "app";
import { Services } from "./services.js";
export default {
    props: ["repositoryId", "changesetRevision", "toolshedUrl"],
    data() {
        const galaxy = getGalaxyInstance();
        return {
            modalShow: true,
            toolConfigs: [],
            toolConfig: null,
            toolSections: [],
            toolSection: null,
            toolConfig: null,
            toolConfigs: galaxy.config.tool_configs
        };
    },
    method: {
        created() {
            toolConfig = this.toolConfigs[0];
            this.configureToolSections();
        },
        configureToolSections() {
            const galaxy = getGalaxyInstance();
            const sections = galaxy.config.toolbox_in_panel;
            this.toolSections = sections.filter(x => x.model_class == "ToolSection").map(x => x.name);
        },
        installRepository: function(details) {
            this.services.installRepository({
                tool_shed_url: this.toolshedUrl,
                repositories: [[this.repositoryId, this.changesetRevision]]
            }).then(response => {
                window.console.log(response);
                /*setTimeout(() => {
                    this.services
                        .getInstalled(this.repo)
                }, 1000);*/
            }).catch(error => {
                alert(error);
            });
        },
    }
};
</script>
