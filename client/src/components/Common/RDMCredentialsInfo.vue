<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { RouterLink } from "vue-router";

import type { BrowsableFilesSourcePlugin } from "@/api/remoteFiles";

interface Props {
    selectedRepository?: BrowsableFilesSourcePlugin;
    isPrivateFileSource?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    selectedRepository: undefined,
    isPrivateFileSource: undefined,
});

const repositoryName = props.selectedRepository?.label ?? "选择的存储库";
</script>

<template>
    <BAlert show variant="info">
        如果您还没有这样做，您可能需要为 {{ repositoryName }} 设置您的凭据

        <span v-if="isPrivateFileSource && selectedRepository">
            在您的
            <RouterLink :to="`/file_source_instances/${selectedRepository.id}/edit`" target="_blank">
                远程文件源设置
            </RouterLink>
        </span>
        <span v-else>
            <span v-if="!isPrivateFileSource">
                在您的 <RouterLink to="/user/information" target="_blank">偏好设置页面</RouterLink>
            </span>
            或在您的 <RouterLink to="/file_sources/index" target="_blank">远程文件源</RouterLink> 部分
        </span>
        以便能够导出。您还可以在这些设置中定义一些导出的默认选项，例如您希望与记录关联的公开名称。
    </BAlert>
</template>