<template>
    <div>
        <div v-if="workflow">
            <h1 class="mb-4 h-lg">导出工作流 `{{ workflow.name }}`</h1>
            <div v-if="workflow.importable && workflow.slug">
                <a :href="importUrl">{{ importUrl }}</a>
                <div>
                    <small>
                        使用此URL可直接将工作流导入到另一个Galaxy服务器。您可以将其复制到导入工作流时的输入字段中。
                    </small>
                </div>
                <hr />
            </div>
            <b-alert v-else variant="info" show>
                此工作流不可访问。请使用共享选项"使工作流可访问并发布"以获取可导入到其他Galaxy的URL。
            </b-alert>
            <a :href="downloadUrl">下载工作流</a>
            <div>
                <small class="text-muted">
                    下载可保存或导入到其他Galaxy服务器的文件。
                </small>
            </div>
            <hr />
            <a :href="svgUrl">创建图像</a>
            <div>
                <small class="text-muted">以SVG格式下载工作流图像。</small>
            </div>
        </div>
        <b-alert v-else-if="!!error" variant="danger" show>
            <span>
                {{ error }}。点击
                <router-link class="require-login-link" to="/login/start">此处</router-link>
                登录。
            </span>
        </b-alert>
        <LoadingSpan v-else message="正在加载工作流" />
    </div>
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import LoadingSpan from "components/LoadingSpan";
import { withPrefix } from "utils/redirect";
import { urlData } from "utils/url";
import Vue from "vue";

Vue.use(BootstrapVue);

export default {
    components: {
        LoadingSpan,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            error: null,
            workflow: null,
        };
    },
    computed: {
        downloadUrl() {
            return withPrefix(`/api/workflows/${this.workflow.id}/download?format=json-download`);
        },
        importUrl() {
            const location = window.location;
            const url = withPrefix(`/u/${this.workflow.owner}/w/${this.workflow.slug}/json`);
            return `${location.protocol}//${location.host}${url}`;
        },
        svgUrl() {
            return withPrefix(`/workflow/gen_image?id=${this.workflow.id}`);
        },
    },
    watch: {
        id() {
            this.getWorkflow();
        },
    },
    created() {
        this.getWorkflow();
    },
    methods: {
        getWorkflow() {
            const url = `/api/workflows/${this.id}`;
            urlData({ url })
                .then((workflow) => {
                    this.workflow = workflow;
                    this.error = null;
                })
                .catch((message) => {
                    this.error = message || "加载工具流失败.";
                });
        },
    },
};
</script>
