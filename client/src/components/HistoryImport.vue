<template>
    <div class="history-import-component" aria-labelledby="history-import-heading">
        <h1 id="history-import-heading" class="h-lg">
            从归档导入 {{ identifierText }}
        </h1>

        <b-alert v-if="errorMessage" variant="danger" dismissible show @dismissed="errorMessage = null">
            {{ errorMessage }}
            <JobError
                v-if="jobError"
                style="margin-top: 15px"
                :header="`${identifierTextCapitalized} 导入作业发生错误`"
                :job="jobError" />
        </b-alert>

        <div v-if="initializing">
            <LoadingSpan message="正在加载服务器配置。" />
        </div>
        <div v-else-if="waitingOnJob">
            <LoadingSpan :message="`等待 ${identifierText} 导入作业，这可能需要一些时间。`" />
        </div>
        <div v-else-if="complete">
            <b-alert :show="complete" variant="success" dismissible @dismissed="complete = false">
                <span class="mb-1 h-sm">完成！</span>
                <p>
                    {{ identifierTextCapitalized }} 已导入，查看
                    <router-link :to="linkToList">您的 {{ identifierTextPlural }}</router-link>
                </p>
            </b-alert>
        </div>
        <div v-else>
            <b-form @submit.prevent="submit">
                <b-form-group v-slot="{ ariaDescribedby }" label="您希望如何指定历史记录归档？">
                    <b-form-radio-group
                        v-model="importType"
                        :aria-describedby="ariaDescribedby"
                        name="import-type"
                        stacked>
                        <b-form-radio value="externalUrl">
                            来自另一个 Galaxy 实例的导出 URL
                            <FontAwesomeIcon icon="external-link-alt" />
                        </b-form-radio>
                        <b-form-radio value="upload">
                            从您的计算机上传本地文件
                            <FontAwesomeIcon icon="upload" />
                        </b-form-radio>
                        <b-form-radio v-if="hasFileSources" value="remoteFilesUri">
                            选择远程文件（例如 Galaxy 的 FTP）
                            <FontAwesomeIcon icon="folder-open" />
                        </b-form-radio>
                    </b-form-radio-group>
                </b-form-group>

                <b-form-group v-if="importType === 'externalUrl'" label="历史归档 URL">
                    <b-alert v-if="showImportUrlWarning" variant="warning" show>
                        看起来您正在尝试从另一个 Galaxy 实例导入已发布的历史记录。您只能通过归档 URL 导入历史记录。
                        <ExternalLink
                            href="https://training.galaxyproject.org/training-material/faqs/galaxy/histories_transfer_entire_histories_from_one_galaxy_server_to_another.html">
                            阅读更多 GTN 文档
                        </ExternalLink>
                    </b-alert>

                    <b-form-input v-model="sourceURL" type="url" />
                </b-form-group>
                <b-form-group v-else-if="importType === 'upload'" label="历史归档文件">
                    <b-form-file v-model="sourceFile" />
                </b-form-group>
                <b-form-group v-show="importType === 'remoteFilesUri'" label="远程文件">
                    <!-- 使用 v-show 以便我们可以持久化引用并在选择时启动对话框 -->
                    <FilesInput ref="filesInput" v-model="sourceRemoteFilesUri" />
                </b-form-group>

                <b-button class="import-button" variant="primary" type="submit" :disabled="!importReady">
                    导入 {{ identifierText }}
                </b-button>
            </b-form>
        </div>
    </div>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExternalLinkAlt, faFolderOpen, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { refDebounced } from "@vueuse/core";
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import JobError from "components/JobInformation/JobError";
import { waitOnJob } from "components/JobStates/wait";
import LoadingSpan from "components/LoadingSpan";
import { getAppRoot } from "onload/loadConfig";
import { errorMessageAsString } from "utils/simple-error";
import { capitalizeFirstLetter } from "utils/strings";
import Vue, { ref, watch } from "vue";

import { fetchFileSources } from "@/api/remoteFiles";

import ExternalLink from "./ExternalLink";

import FilesInput from "components/FilesDialog/FilesInput.vue";

library.add(faFolderOpen);
library.add(faUpload);
library.add(faExternalLinkAlt);
Vue.use(BootstrapVue);

export default {
    components: { FilesInput, FontAwesomeIcon, JobError, LoadingSpan, ExternalLink },
    props: {
        invocationImport: {
            type: Boolean,
            default: false,
        },
    },
    setup() {
        const sourceURL = ref("");
        const debouncedURL = refDebounced(sourceURL, 200);
        const mayBeHistoryUrlRegEx = /\/u(ser)?\/.+\/h(istory)?\/.+/;

        const showImportUrlWarning = ref(false);

        watch(
            () => debouncedURL.value,
            (val) => {
                const url = val ?? "";
                showImportUrlWarning.value = Boolean(url.match(mayBeHistoryUrlRegEx));
            }
        );

        return {
            sourceURL,
            showImportUrlWarning,
        };
    },
    data() {
        return {
            initializing: true,
            importType: "externalUrl",
            sourceFile: null,
            sourceRemoteFilesUri: "",
            errorMessage: null,
            waitingOnJob: false,
            complete: false,
            jobError: null,
            hasFileSources: false,
        };
    },
    computed: {
        importReady() {
            const importType = this.importType;
            if (importType == "externalUrl") {
                return !!this.sourceURL;
            } else if (importType == "upload") {
                return !!this.sourceFile;
            } else if (importType == "remoteFilesUri") {
                return !!this.sourceRemoteFilesUri;
            } else {
                return false;
            }
        },
        linkToList() {
            return this.invocationImport ? `/workflows/invocations` : `/histories/list`;
        },
        identifierText() {
        return this.invocationImport ? "调用" : "历史记录";
        },
        identifierTextCapitalized() {
            return capitalizeFirstLetter(this.identifierText);
        },
        identifierTextPlural() {
            return this.invocationImport ? "调用记录" : "历史记录";
        },
    },
    watch: {
        importType() {
            if (this.importType == "remoteFilesUri" && !this.sourceRemoteFilesUri) {
                this.$refs.filesInput.selectFile();
            }
        },
    },
    async mounted() {
        await this.initialize();
    },
    methods: {
        async initialize() {
            const fileSources = await fetchFileSources();
            this.hasFileSources = fileSources.length > 0;
            this.initializing = false;
        },
        submit: function (ev) {
            const formData = new FormData();
            const importType = this.importType;
            if (importType == "externalUrl") {
                formData.append("archive_source", this.sourceURL);
            } else if (importType == "upload") {
                formData.append("archive_file", this.sourceFile);
                formData.append("archive_source", "");
            } else if (importType == "remoteFilesUri") {
                formData.append("archive_source", this.sourceRemoteFilesUri);
            }
            axios
                .post(`${getAppRoot()}api/histories`, formData)
                .then((response) => {
                    this.waitingOnJob = true;
                    waitOnJob(response.data.id)
                        .then((jobResponse) => {
                            this.waitingOnJob = false;
                            this.complete = true;
                        })
                        .catch(this.handleError);
                })
                .catch(this.handleError);
        },
        handleError: function (err) {
            this.waitingOnJob = false;
            this.errorMessage = errorMessageAsString(err, "历史记录导入失败.");
            if (err?.data?.stderr) {
                this.jobError = err.data;
            }
        },
    },
};
</script>

<style scoped>
.error-wrapper {
    margin-top: 10px;
}
</style>
