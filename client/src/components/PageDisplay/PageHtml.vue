<template>
    <div>
        <div v-for="(child, childIndex) in childList" :key="childIndex">
            <p v-html="child" />
        </div>
    </div>
</template>

<script>
import { withPrefix } from "utils/redirect";

export default {
    props: {
        page: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            childList: [],
        };
    },
    watch: {
        page() {
            this.processHtml(this.page.content);
        },
    },
    methods: {
        processHtml(content) {
            this.childList = [];
            if (content) {
                const vDom = document.createElement("div");
                vDom.innerHTML = content;
                const children = Array.from(vDom.children);
                children.forEach((child) => {
                    if (child.classList.contains("embedded-item")) {
                        const splitId = child.id.split("-");
                        if (splitId.length == 2) {
                            const [modelClass, modelId] = splitId;
                            this.childList.push(this.processItem(modelClass, modelId));
                        } else {
                            this.childList.push(`无法解析项目标识符: ${child.id}.`);
                        }
                    } else {
                        this.childList.push(child.innerHTML);
                    }
                });
            }
        },
        processItem(modelClass, modelId) {
            let html = null;
            if (modelClass == "StoredWorkflow") {
                const url = withPrefix(`/published/workflow?id=${modelId}`);
                html = `<a href='${url}'>查看工作流<a>`;
            } else if (modelClass == "History") {
                const url = withPrefix(`/published/history?id=${modelId}`);
                html = `<a href='${url}'>查看历史<a>`;
            } else if (modelClass == "HistoryDatasetAssociation") {
                const url = withPrefix(`/datasets/${modelId}/preview`);
                html = `<a href='${url}'>查看数据集<a>`;
            } else if (modelClass == "Visualization") {
                const url = withPrefix(`/published/history?id=${modelId}`);
                html = `<a href='${url}'>查看可视化<a>`;
            } else {
                html = `类型为'${modelClass}'的项目无法嵌入。`;
            }
            return `<p>${html}</p>`;
        },
    },
};
</script>
