<template>
    <b-modal v-model="modalShow" @ok="onOk" @hide="onHide">
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
            <b-form-checkbox v-model="installResolverDependencies" >
                Install resolvable dependencies
            </b-form-checkbox>
            <b-form-checkbox v-model="installRepositoryDependencies" >
                Install repository dependencies
            </b-form-checkbox>
            <b-form-checkbox v-model="installToolDependencies" >
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
            installToolDependencies: true,
            installRepositoryDependencies: true,
            installResolverDependencies: true,
            toolConfigs: [],
            toolConfig: null,
            toolSections: [],
            toolSection: null,
        };
    },
    computed: {
        modalTitle() {
            return `Installing '${this.repo.name}'`;
        }
    },
    created() {
        this.services = new Services();
        this.loadConfig();
    },
    methods: {
        loadConfig: function() {
            const galaxy = getGalaxyInstance();
            const sections = galaxy.config.toolbox_in_panel;
            this.toolSections = sections.filter(x => x.model_class == "ToolSection").map(x => x.name);
            this.toolConfigs = galaxy.config.tool_configs || [];
            this.toolConfig = this.toolConfigs[0];
        },
        onOk: function() {
            this.services.installRepository({
                tool_shed_url: this.toolshedUrl,
                name: this.repo.name,
                owner: this.repo.repo_owner_username,
                changeset_revision: this.repoChangeset,
                //new_tool_panel_section_label or tool_panel_section_id, tool_section: this.toolSection,
                //shed_tool_conf, tool_configuration: this.toolConfig,
                install_resolver_dependencies: this.installResolverDependencies,
                install_tool_dependencies: this.installToolDependencies,
                install_repository_dependencies: this.installRepositoryDependencies
            }).then(response => {
                window.console.log(response);
                this.$emit("ok");
            }).catch(error => {
            });
        },
        onHide: function() {
            this.$emit("hide");
        }
    }
};
</script>
