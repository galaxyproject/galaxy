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
        <div class="revision text-muted small mb-3">{{ repo.owner }} 修订版本 {{ changesetRevision }}</div>
        <b-form-group
            v-if="requiresPanel"
            label="目标分区："
            description="选择现有工具面板分区或创建新分区来容纳安装的工具（可选）。">
            <b-form-input v-model="toolSection" list="sectionSelect" />
            <datalist id="sectionSelect">
                <option v-for="section in toolSections" :key="section.id">
                    {{ section.name }}
                </option>
            </datalist>
        </b-form-group>
        <b-link variant="primary" @click="onAdvanced"> {{ advancedTitle }} 高级设置 </b-link>
        <b-collapse id="advanced-collapse" v-model="advancedShow" class="mt-2">
            <b-card>
                <b-form-group v-if="showConfig" label="工具配置：" description="选择工具配置。">
                    <b-form-radio
                        v-for="filename in toolConfigs"
                        :key="filename"
                        v-model="toolConfig"
                        :value="filename">
                        {{ filename }}
                    </b-form-radio>
                </b-form-group>
                <b-form-group label="依赖项：" description="选择如何处理依赖项。">
                    <b-form-checkbox v-model="installResolverDependencies">
                        安装可解析的依赖项
                    </b-form-checkbox>
                    <b-form-checkbox v-model="installRepositoryDependencies">
                        安装存储库依赖项
                    </b-form-checkbox>
                    <b-form-checkbox v-model="installToolDependencies"> 安装工具依赖项 </b-form-checkbox>
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
            return this.advancedShow ? "隐藏" : "显示";
        },
        modalTitle() {
            return `正在安装 '${this.repo.name}'`;
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
