<script setup lang="ts">
import { RouterLink } from "vue-router"
</script>
<template>
    <div class="landing-info-sections">
        <div class="info-section q-py-lg">
            <div class="row items-start">
                <q-icon name="search" color="primary" size="48px" class="q-mr-lg" />
                <div class="info-text">
                    <div class="text-h6 text-weight-bold">Find</div>
                    <div class="text-body1">
                        <router-link to="/repositories_by_category">Browse repositories by category</router-link> or
                        <router-link to="/repositories_by_owner">by owner</router-link>.
                    </div>
                </div>
            </div>
        </div>

        <q-separator />

        <div class="info-section q-py-lg">
            <div class="row items-start justify-end">
                <div class="info-text text-right">
                    <div class="text-h6 text-weight-bold">Install</div>
                    <div class="text-body1">
                        Learn how to install tools in Galaxy from the
                        <a
                            href="https://training.galaxyproject.org/training-material/topics/admin/tutorials/tool-management/tutorial.html"
                            target="_blank"
                            >Galaxy Training Network tutorial</a
                        >.
                    </div>
                </div>
                <q-icon name="download" color="primary" size="48px" class="q-ml-lg" />
            </div>
        </div>

        <q-separator />

        <div class="info-section q-py-lg">
            <div class="row items-start">
                <q-icon name="upload" color="primary" size="48px" class="q-mr-lg" />
                <div class="info-text">
                    <div class="text-h6 text-weight-bold">Publish</div>
                    <div class="text-body1">
                        Share your tools with the community using
                        <a href="https://planemo.readthedocs.io/en/latest/publishing.html" target="_blank">Planemo</a>.
                    </div>
                </div>
            </div>
        </div>

        <q-separator />

        <div class="info-section q-py-lg">
            <div class="row items-start justify-end">
                <div class="info-text text-right">
                    <div class="text-h6 text-weight-bold">Cite</div>
                    <div class="text-body1">
                        Information on citing the Tool Shed is available on the
                        <a href="https://galaxyproject.org/citing-galaxy/#toolshed" target="_blank">Galaxy Hub</a>.
                    </div>
                </div>
                <q-icon name="format_quote" color="primary" size="48px" class="q-ml-lg" />
            </div>
        </div>
    </div>
</template>

<style scoped>
.info-text {
    max-width: 280px;
}
</style>
