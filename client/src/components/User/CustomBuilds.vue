<template>
    <b-container>
        <b-row>
            <b-col>
                <h1 class="h-sm">当前自定义基因组</h1>
            </b-col>
        </b-row>
        <b-row>
            <b-col>
                <b-table small show-empty class="grid" :items="customBuilds" :fields="fields">
                    <template v-slot:cell(action)="row">
                        <a
                            v-b-tooltip.bottom.hover
                            href="javascript:void(0)"
                            title="删除基因组"
                            @click="deleteBuild(row.item.id)">
                            <i class="icon fa fa-lg fa-trash-o" />
                        </a>
                    </template>
                </b-table>
            </b-col>
        </b-row>
        <template v-if="installedBuilds.length > 0">
            <b-row class="mt-2">
                <b-col>
                    <h2 class="h-sm">系统安装的基因组</h2>
                </b-col>
            </b-row>
            <b-row>
                <b-col id="installed-builds" class="mb-4">
                    <Multiselect
                        v-model="selectedInstalledBuilds"
                        multiple
                        taggable
                        label="label"
                        track-by="value"
                        :searchable="false"
                        :options="installedBuilds">
                    </Multiselect>
                </b-col>
            </b-row>
        </template>
        <b-row>
            <b-col>
                <h2 class="h-sm">添加自定义基因组</h2>
            </b-col>
        </b-row>
        <b-row>
            <b-col>
                <b-card>
                    <b-alert
                        fade
                        dismissible
                        :variant="alertType"
                        :show="dismissCountDown"
                        @dismissed="dismissCountDown = 0"
                        @dismiss-count-down="countDownChanged">
                        {{ alertMessage }}
                    </b-alert>

                    <b-form @submit.prevent="save">
                        <b-form-group label="名称" description="指定基因组名称，例如：仓鼠。" label-for="name">
                            <b-form-input id="name" v-model="form.name" tour_id="name" required />
                        </b-form-group>
                        <b-form-group label="键值" description="指定基因组键值，例如：hamster_v1。" label-for="id">
                            <b-form-input id="id" v-model="form.id" tour_id="id" required />
                        </b-form-group>
                        <b-form-group label="定义" description="提供数据源。" label-for="type">
                            <b-form-select
                                id="type"
                                v-model="selectedDataSource"
                                tour_id="type"
                                :options="dataSources"></b-form-select>
                        </b-form-group>
                        <div>
                            <b-form-group v-if="selectedDataSource === 'fasta'" label="FASTA文件">
                                <b-form-select
                                    v-model="selectedFastaFile"
                                    :options="fastaFiles"
                                    :disabled="fastaFilesSelectDisabled"></b-form-select>
                            </b-form-group>
                            <b-form-group v-if="selectedDataSource === 'file'" label="Len文件">
                                <b-form-file placeholder="选择文件..." @change="readFile" />
                                <b-progress
                                    v-show="fileLoaded !== 0"
                                    animated
                                    show-progress
                                    :value="fileLoaded"
                                    :max="maxFileSize" />
                                <b-form-textarea v-show="form.file" :value="form.file" />
                            </b-form-group>
                            <b-form-group v-if="selectedDataSource === 'text'" label="编辑/粘贴">
                                <b-form-textarea id="len-file-text-area" v-model="form.text" />
                            </b-form-group>
                        </div>

                        <b-button
                            id="save"
                            v-b-tooltip.bottom.hover
                            type="submit"
                            variant="primary"
                            title="创建新基因组">
                            <i class="icon fa fa-save" /> 保存
                        </b-button>
                    </b-form>
                </b-card>
            </b-col>
            <b-col>
                <b-card v-if="selectedDataSource === 'fasta'" class="alert-info">
                    <h2 class="h-sm">FASTA格式</h2>
                    <p class="card-text">
                        这是一个来自您当前历史记录的多FASTA文件，它为您基因组中的每个染色体/片段提供基因组序列。
                    </p>
                    <p class="card-text">以下是多FASTA文件的示例片段：</p>
                    <pre class="card-text">
&gt;chr1
ATTATATATAAGACCACAGAGAGAATATTTTGCCCGG...

&gt;chr2
GGCGGCCGCGGCGATATAGAACTACTCATTATATATA...

...</pre
                    >
                </b-card>
                <b-card v-else class="alert-info">
                    <h2 class="h-sm">长度格式</h2>
                    <p class="card-text">长度格式由两列组成，以空格分隔，格式如下：</p>
                    <pre class="card-text">染色体/片段   染色体/片段的长度</pre>
                    <p class="card-text">例如，<em>mm9.len</em>的前几个条目如下：</p>
                    <pre class="card-text">
chr1    197195432
chr2    181748087
chr3    159599783
chr4    155630120
chr5    152537259</pre
                    >
                    <p class="card-text">
                        Trackster使用此信息填充染色体/片段的选择框，并设置轨道浏览器的最大碱基对。您可以上传此格式的.len文件（Len文件选项），或直接在框中输入信息（Len条目选项）。
                    </p>
                </b-card>
            </b-col>
        </b-row>
    </b-container>
</template>

<script>
import "vue-multiselect/dist/vue-multiselect.min.css";

import { getGalaxyInstance } from "app";
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";
import Multiselect from "vue-multiselect";

Vue.use(BootstrapVue);

export default {
    components: {
        Multiselect,
    },
    data() {
        const Galaxy = getGalaxyInstance();
        return {
            customBuildsUrl: `${Galaxy.root}api/users/${Galaxy.user.id}/custom_builds`,
            selectedInstalledBuilds: [],
            installedBuilds: [],
            maxFileSize: 100,
            fileLoaded: 0,
            fields: [
                { key: "name", label: "名称" },
                { key: "id", label: "键值" },
                { key: "count", label: "染色体/片段数量" },
                { key: "action", label: "" },
            ],
            customBuilds: [],
            alertType: "info",
            alertMessage: "",
            dismissSecs: 5,
            dismissCountDown: 0,
            form: {
                id: "",
                name: "",
                file: "",
                text: "",
            },
            dataSources: [
                { value: "fasta", text: "来自历史记录的FASTA文件" },
                { value: "file", text: "来自磁盘的Len文件" },
                { value: "text", text: "通过复制/粘贴的Len文件" },
            ],
            selectedDataSource: "fasta",
            fastaFilesLoading: true,
            fastaFilesSelectDisabled: true,
            fastaFiles: [],
            selectedFastaFile: null,
        };
    },
    computed: {
        lengthType: function () {
            return this.selectedDataSource || "";
        },
        lengthValue: function () {
            let value = "";
            if (this.lengthType === "fasta") {
                value = this.selectedFastaFile || "";
            } else if (this.lengthType === "file") {
                value = this.form.file;
            } else if (this.lengthType === "text") {
                value = this.form.text;
            }
            return value;
        },
    },
    created() {
        const Galaxy = getGalaxyInstance();
        const historyId = Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.model.id;
        this.loadCustomBuilds();
        if (historyId) {
            this.loadCustomBuildsMetadata(historyId);
        } else {
            this.fastaFilesLoading = false;
        }
    },
    methods: {
        loadCustomBuilds() {
            axios
                .get(this.customBuildsUrl)
                .then((response) => {
                    this.customBuilds = response.data;
                })
                .catch((error) => {
                    this.showAlert("danger", error.response);
                });
        },
        loadCustomBuildsMetadata(historyId) {
            const Galaxy = getGalaxyInstance();
            axios
                .get(`${Galaxy.root}api/histories/${historyId}/custom_builds_metadata`)
                .then((response) => {
                    const fastaHdas = response.data.fasta_hdas;
                    for (let i = 0; i < fastaHdas.length; i++) {
                        fastaHdas[i].text = fastaHdas[i].label;
                    }
                    if (fastaHdas && fastaHdas.length > 0) {
                        this.fastaFiles = fastaHdas;
                        this.selectedFastaFile = fastaHdas[0].value;
                        this.fastaFilesSelectDisabled = false;
                    }
                    this.fastaFilesLoading = false;
                    this.installedBuilds = response.data.installed_builds;
                    for (let i = 0; i < this.installedBuilds.length; i++) {
                        this.installedBuilds[i].text = this.installedBuilds[i].label;
                    }
                })
                .catch((error) => {
                    this.showAlert("danger", error.response);
                    this.fastaFilesLoading = false;
                });
        },
        save(event) {
            const data = {
                id: this.form.id,
                name: this.form.name,
                "len|type": this.lengthType,
                "len|value": this.lengthValue,
            };
            if (!data.id.trim() || !data.name.trim() || !data["len|value"].trim()) {
                this.showAlert("danger", "所有输入都是必需的。");
                return false;
            }
            axios
                .put(`${this.customBuildsUrl}/${data.id}`, data)
                .then((response) => {
                    if (response.data.message) {
                        this.showAlert("warning", response.data.message);
                    } else {
                        this.showAlert("success", "成功添加新的自定义基因组。");
                    }
                    this.loadCustomBuilds();
                })
                .catch((error) => {
                    const message = error.response.data.err_msg;
                    this.showAlert("danger", message || "创建自定义基因组失败。");
                });
        },
        deleteBuild(id) {
            axios
                .delete(`${this.customBuildsUrl}/${id}`)
                .then((response) => {
                    this.customBuilds = this.customBuilds.filter((i) => i.id !== id);
                })
                .catch((error) => {
                    const message = error.response.data.err_msg;
                    this.showAlert("danger", message || "删除自定义基因组失败。");
                });
        },
        readFile(event) {
            const file = event.target.files && event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onprogress = (e) => {
                    if (e.lengthComputable) {
                        this.fileLoaded = Math.round(e.loaded / e.total) * 100;
                    }
                };
                reader.onload = () => {
                    this.fileLoaded = 0;
                    this.form.file = reader.result;
                };
                reader.readAsText(file);
            }
        },
        showAlert(type, message) {
            this.alertType = type;
            this.alertMessage = message;
            this.dismissCountDown = this.dismissSecs;
        },
        countDownChanged(dismissCountDown) {
            this.dismissCountDown = dismissCountDown;
        },
    },
};
</script>

<style scoped>
.fa-trash-o {
    color: initial;
}
</style>
