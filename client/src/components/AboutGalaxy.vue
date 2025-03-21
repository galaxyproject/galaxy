<script setup lang="ts">
/* global __buildTimestamp__, __license__  */
/* (injected by webpack) */

import { computed } from "vue";
import { RouterLink } from "vue-router";

import { useConfig } from "@/composables/config";
import { getAppRoot } from "@/onload/loadConfig";

import Heading from "@/components/Common/Heading.vue";
import ExternalLink from "@/components/ExternalLink.vue";
import License from "@/components/License/License.vue";
import UtcDate from "@/components/UtcDate.vue";

const { config, isConfigLoaded } = useConfig();

const clientBuildDate = __buildTimestamp__ || new Date().toISOString();
const apiDocsLink = `${getAppRoot()}api/docs`;
const galaxyLicense = __license__;

const versionUserDocumentationUrl = computed(() => {
    const configVal = config.value;
    return config.value.version_minor.slice(0, 3) === "dev"
        ? "https://docs.galaxyproject.org/en/latest/releases/index.html"
        : `${configVal.release_doc_base_url}${configVal.version_major}/releases/${configVal.version_major}_announce_user.html`;
});
</script>

<template>
    <div v-if="isConfigLoaded" class="about-galaxy">
        <Heading h1 :icon="['gxd', 'galaxyLogo']" size="lg">帮助与支持</Heading>
        <div class="p-2">
            <Heading h2 separator size="md">支持</Heading>
            <div v-if="config.wiki_url">
                <ExternalLink :href="config.wiki_url">
                    <strong v-localize>社区中心</strong>
                </ExternalLink>
                <p v-localize>加入我们的社区，探索 Galaxy 的使用教程，提高您的技能。</p>
            </div>
            <div v-if="config.helpsite_url">
                <ExternalLink :href="config.helpsite_url">
                    <strong v-localize>提问与解答</strong>
                </ExternalLink>
                <p v-localize>
                    访问 Galaxy 问答网站，查找问题的答案，并与其他用户交流。
                </p>
            </div>
            <div v-if="config.support_url">
                <ExternalLink :href="config.support_url">
                    <strong v-localize>联系我们</strong>
                </ExternalLink>
                <p v-localize>需要帮助，或想要学习和教授更多关于 Galaxy 的知识？欢迎与我们联系。</p>
            </div>
            <Heading v-localize h2 separator size="md">帮助</Heading>
            <div>
                <RouterLink to="tours">
                    <strong v-localize>交互式教程</strong>
                </RouterLink>
                <p v-localize>通过交互式教程了解和学习 Galaxy。</p>
            </div>
            <div v-if="config.screencasts_url">
                <ExternalLink :href="config.screencasts_url">
                    <strong v-localize>视频与演示</strong>
                </ExternalLink>
                <p v-localize>观看视频和演示，进一步了解 Galaxy。</p>
            </div>
            <div v-if="config.citation_url">
                <ExternalLink :href="config.citation_url">
                    <strong v-localize>如何引用我们</strong>
                </ExternalLink>
                <p v-localize>查看如何正确引用 Galaxy 的相关信息。</p>
            </div>
            <Heading h2 separator size="md">技术详情</Heading>
            <div>
                <!-- Galaxy 版本信息，包含到发布说明的链接 -->
                <ExternalLink :href="versionUserDocumentationUrl">
                    <strong v-localize>版本说明</strong>
                </ExternalLink>
                <p v-localize>
                    当前 Galaxy 服务器版本为
                    <strong>{{ config.version_major }}.{{ config.version_minor }}</strong
                    >，Web 客户端构建于
                    <strong><UtcDate :date="clientBuildDate" mode="pretty" /></strong>。
                </p>
                <template v-if="config.version_extra">
                    <p v-localize>服务器还提供了以下额外的版本信息：</p>
                    <ul>
                        <li v-for="([name, value], index) in Object.entries(config.version_extra)" :key="index">
                            <strong>{{ name }}</strong>
                            ：{{ value }}
                        </li>
                    </ul>
                </template>
            </div>
            <div>
                <ExternalLink :href="apiDocsLink">
                    <strong v-localize>API 文档</strong>
                </ExternalLink>
                <p v-localize>探索 Galaxy API。</p>
            </div>
            <div>
                <License class="font-weight-bold" :license-id="galaxyLicense" />
                <p v-localize>Galaxy 软件遵循 MIT 许可证。</p>
            </div>
            <div v-if="config.terms_url">
                <!-- 若有可用的使用条款 -->
                <ExternalLink :href="config.terms_url">
                    <strong v-localize>使用条款</strong>
                </ExternalLink>
                <p v-localize>
                    本 Galaxy 服务器规定了适用于服务使用的相关条款与条件。
                </p>
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.about-galaxy h1 {
    --fa-primary-color: #{$brand-primary};
    --fa-secondary-color: #{$brand-toggle};
    --fa-secondary-opacity: 1;
}
</style>
