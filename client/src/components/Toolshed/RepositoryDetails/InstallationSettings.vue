<template>
    <GModal
        id="repo-install-settings"
        v-model:show="modalShow"
        size="small"
        :title="modalTitle"
        confirm
        @ok="onOk"
        @close="onHide">
        <div class="description mb-1">
            {{ repo.long_description || repo.description }}
        </div>
        <div class="revision text-muted small mb-3">{{ repo.owner }} rev. {{ changesetRevision }}</div>
        <BFormGroup
            v-if="requiresPanel"
            label="Target Section:"
            description="Choose an existing tool panel section or create a new section to contain the installed tools (optional).">
            <BFormInput v-model="toolSection" list="sectionSelect" />
            <datalist id="sectionSelect">
                <option v-for="section in toolSections" :key="section.id">
                    {{ section.name }}
                </option>
            </datalist>
        </BFormGroup>
        <Heading separator size="sm" :collapse="advancedShow ? 'open' : 'closed'" @click="onAdvanced">
            {{ advancedTitle }} advanced settings
        </Heading>
        <GCollapse v-model="advancedShow" class="mt-2">
            <BCard>
                <BFormGroup
                    v-if="toolConfigs.length > 1"
                    label="Tool Configuration:"
                    description="Choose a tool configuration.">
                    <BFormRadio v-for="filename in toolConfigs" :key="filename" v-model="toolConfig" :value="filename">
                        {{ filename }}
                    </BFormRadio>
                </BFormGroup>
                <BFormGroup label="Dependencies:" description="Choose how to handle dependencies.">
                    <BFormCheckbox v-model="installResolverDependencies">
                        Install resolvable dependencies
                    </BFormCheckbox>
                    <BFormCheckbox v-model="installRepositoryDependencies">
                        Install repository dependencies
                    </BFormCheckbox>
                    <BFormCheckbox v-model="installToolDependencies"> Install tool dependencies </BFormCheckbox>
                </BFormGroup>
            </BCard>
        </GCollapse>
    </GModal>
</template>
<script>
import { BCard, BFormCheckbox, BFormGroup, BFormInput, BFormRadio } from "bootstrap-vue";

import { GalaxyApi } from "@/api";
import { useConfig } from "@/composables/config";

import GCollapse from "@/components/BaseComponents/GCollapse.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import Heading from "@/components/Common/Heading.vue";

export default {
    components: {
        BCard,
        BFormCheckbox,
        BFormGroup,
        BFormInput,
        BFormRadio,
        GCollapse,
        GModal,
        Heading,
    },
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
    },
    setup() {
        const { config, isConfigLoaded } = useConfig(true);
        return { config, isConfigLoaded };
    },
    data() {
        return {
            modalShow: true,
            advancedShow: false,
            installToolDependencies: this.config.install_tool_dependencies,
            installRepositoryDependencies: this.config.install_repository_dependencies,
            installResolverDependencies: this.config.install_resolver_dependencies,
            toolConfig: null,
            toolConfigs: [],
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
        toolSections() {
            const panel = Object.values(this.currentPanel);
            if (panel) {
                return panel.filter((x) => x.tools);
            } else {
                return [];
            }
        },
    },
    async created() {
        const { data, error } = await GalaxyApi().GET("/api/configuration/dynamic_tool_confs");
        if (error) {
            console.error("Failed to collect dynamic tool confs", error.err_msg);
        } else if (data.length > 0) {
            this.toolConfigs = data.map((x) => x.config_filename);
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
