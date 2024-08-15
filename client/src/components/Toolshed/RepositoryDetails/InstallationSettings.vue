<template>
    <b-modal id="repo-install-settings" v-model="modalShow" :static="modalStatic" @ok="onOk" @hide="onHide">
        <template v-slot:modal-header>
            <h2 class="title m-0 h-sm">
                {{ modalTitle }}
            </h2>
        </template>
        <div class="description mb-1">
            {{ repo.long_description || repo.description }}
        </div>
        <div class="revision text-muted small mb-3">{{ repo.owner }} rev. {{ changesetRevision }}</div>
        <b-form-group
            v-if="requiresPanel"
            label="Target Section:"
            description="Choose an existing tool panel section or create a new section to contain the installed tools (optional).">
            <b-form-input v-model="toolSection" list="sectionSelect" />
            <datalist id="sectionSelect">
                <option v-for="section in toolSections" :key="section.id">
                    {{ section.name }}
                </option>
            </datalist>
        </b-form-group>
        <b-link variant="primary" @click="onAdvanced"> {{ advancedTitle }} advanced settings. </b-link>
        <b-collapse id="advanced-collapse" v-model="advancedShow" class="mt-2">
            <b-card>
                <b-form-group v-if="showConfig" label="Tool Configuration:" description="Choose a tool configuration.">
                    <b-form-radio
                        v-for="filename in toolConfigs"
                        :key="filename"
                        v-model="toolConfig"
                        :value="filename">
                        {{ filename }}
                    </b-form-radio>
                </b-form-group>
                <b-form-group label="Dependencies:" description="Choose how to handle dependencies.">
                    <b-form-checkbox v-model="installResolverDependencies">
                        Install resolvable dependencies
                    </b-form-checkbox>
                    <b-form-checkbox v-model="installRepositoryDependencies">
                        Install repository dependencies
                    </b-form-checkbox>
                    <b-form-checkbox v-model="installToolDependencies"> Install tool dependencies </b-form-checkbox>
                </b-form-group>
            </b-card>
        </b-collapse>
    </b-modal>
</template>
<script>
export default {
    props: {
        repo: {
            type: Object,
            required: true,
        },
        changesetRevision: {
            type: String,
            required: true,
        },
        requiresPanel: {
            type: Boolean,
            required: true,
        },
        toolshedUrl: {
            type: String,
            required: true,
        },
        currentPanel: {
            type: Object,
            default: null,
        },
        toolDynamicConfigs: {
            type: Array,
            default: null,
        },
        modalStatic: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            modalShow: true,
            advancedShow: false,
            installToolDependencies: true,
            installRepositoryDependencies: true,
            installResolverDependencies: true,
            toolConfig: null,
            toolSection: null,
        };
    },
    computed: {
        advancedTitle() {
            return this.advancedShow ? "Hide" : "Show";
        },
        modalTitle() {
            return `Installing '${this.repo.name}'`;
        },
        showConfig() {
            return this.toolConfigs.length > 1;
        },
        toolSections() {
            const panel = Object.values(this.currentPanel);
            if (panel) {
                return panel.filter((x) => x.tools);
            } else {
                return [];
            }
        },
        toolConfigs() {
            return this.toolDynamicConfigs || [];
        },
    },
    created() {
        if (this.toolConfigs.length > 0) {
            this.toolConfig = this.toolConfigs[0];
        }
    },
    methods: {
        findSection: function (name) {
            const result = ["", ""];
            if (name) {
                const found = this.toolSections.find((s) => {
                    return s.name.toLowerCase().trim() == name.toLowerCase().trim();
                });
                if (found) {
                    result[0] = found.id;
                } else {
                    result[1] = name;
                }
            }
            return result;
        },
        onAdvanced: function () {
            this.advancedShow = !this.advancedShow;
        },
        onOk: function () {
            const [sectionId, sectionLabel] = this.findSection(this.toolSection);
            this.$emit("ok", {
                tool_shed_url: this.toolshedUrl,
                name: this.repo.name,
                owner: this.repo.owner,
                changeset_revision: this.changesetRevision,
                new_tool_panel_section_label: sectionLabel,
                tool_panel_section_id: sectionId,
                shed_tool_conf: this.toolConfig,
                install_resolver_dependencies: this.installResolverDependencies,
                install_tool_dependencies: this.installToolDependencies,
                install_repository_dependencies: this.installRepositoryDependencies,
            });
        },
        onHide: function () {
            this.$emit("hide");
        },
    },
};
</script>
