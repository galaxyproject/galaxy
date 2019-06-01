<template>
    <b-card>
        Test
    </b-card>
</template>
<script>
import { getGalaxyInstance } from "app";
import { Services } from "./services.js";
export default {
    props: ["repositoryId", "changesetRevision", "toolshedUrl"],
    data() {
        const galaxy = getGalaxyInstance();
        return {
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
