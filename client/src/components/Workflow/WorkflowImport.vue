<script setup lang="ts">
import { BTab, BTabs } from "bootstrap-vue";

import FromFileOrUrl from "@/components/Workflow/Import/FromFileOrUrl.vue";
import TrsImport from "@/components/Workflow/Import/TrsImport.vue";
import TrsSearch from "@/components/Workflow/Import/TrsSearch.vue";
</script>

<template>
    <section>
        <h1 class="h-lg">导入工作流</h1>
        <BTabs fill>
            <BTab title-link-class="workflow-import-file-link" title="归档文件或网址" active>
                <FromFileOrUrl />
            </BTab>

            <BTab title-link-class="workflow-import-trs-search-link" title="GA4GH 服务器">
                <div class="mt-4">
                    <h2 class="h-sm">从已配置的 GA4GH 工具注册服务器导入工作流（例如 Dockstore）</h2>

                    <TrsSearch />
                </div>
            </BTab>

            <BTab title-link-class="workflow-import-trs-id-link" title="TRS ID">
                <div class="mt-4">
                    <h2 class="h-sm">从 TRS ID 导入</h2>

                    <TrsImport />
                </div>
            </BTab>
        </BTabs>
    </section>
</template>