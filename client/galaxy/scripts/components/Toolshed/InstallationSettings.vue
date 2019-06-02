<template>
    <b-modal v-model="modalShow">
        <template slot="modal-header">
            <h4 class="m-0">
                {{ modalTitle }}
            </h4>
        </template>
        <div class="mb-1">
            {{ repo.long_description }}
        </div>
        <div class="text-muted small mb-3">
            {{ repo.repo_owner_username }} rev. {{ repoChangeset }}
        </div>
        <b-form-group
            label="Target Section:"
            description="Choose an existing section in your tool panel to contain the installed tools (optional)."
        >
            <b-form-input list="sectionSelect" v-model="toolSection" />
            <datalist id="sectionSelect">
                <option v-for="section in toolSections">{{ section }}</option>
            </datalist>
        </b-form-group>
        <b-form-group
            label="Tool Configuration:"
            description="Choose a tool configuration.">
            <div class="ui-select">
                <b-form-select :options="toolConfigs" v-model="toolConfig" />
            </div>
        </b-form-group>
        <b-form-group
            label="Dependencies:"
            description="Choose how to handle dependencies.">
            <b-form-checkbox v-model="resolvableDependency" >
                Install resolvable dependencies
            </b-form-checkbox>
            <b-form-checkbox v-model="repositoryDependency" >
                Install repository dependencies
            </b-form-checkbox>
            <b-form-checkbox v-model="toolDependency" >
                Install tool dependencies
            </b-form-checkbox>
        </b-form-group>
    </b-modal>
</template>
<script>
import { getGalaxyInstance } from "app";
import { Services } from "./services.js";
export default {
    props: ["repo", "toolshedUrl", "repoChangeset", "repoNumeric"],
    data() {
        return {
            modalShow: true,
            toolConfigs: [],
            toolConfig: null,
            toolSections: [],
            toolSection: null,
            toolConfig: null,
            toolDependency: true,
            repositoryDependency: true,
            resolvableDependency: true
        };
    },
    computed: {
        modalTitle() {
            return `Installing '${this.repo.name}'`;
        }
    },
    created() {
        this.loadConfig();
    },
    methods: {
        loadConfig: function() {
            const galaxy = getGalaxyInstance();
            const sections = galaxy.config.toolbox_in_panel;
            this.toolSections = sections.filter(x => x.model_class == "ToolSection").map(x => x.name);
            this.toolConfigs = galaxy.config.tool_configs;
            this.toolConfig = this.toolConfigs[0];
        },
        installRepository: function(details) {
            this.services.installRepository({
                tool_shed_url: this.toolshedUrl,
                repositories: [[this.repo.id, this.repoChangeset]]
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
