<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faDownload, faMagnifyingGlass, faQuoteLeft, faUpload } from "@fortawesome/free-solid-svg-icons"
import { RouterLink } from "vue-router"
</script>
<template>
    <div class="landing-info-sections">
        <div class="info-section q-py-lg">
            <div class="row items-start">
                <FontAwesomeIcon :icon="faMagnifyingGlass" class="text-primary q-mr-lg" style="font-size: 48px" />
                <div class="info-text">
                    <div class="text-h6 text-weight-bold">Find</div>
                    <div class="text-body1">
                        <router-link to="/repositories_by_category">Browse repositories by category</router-link> or
                        <router-link to="/repositories_by_owner">by owner</router-link>.
                    </div>
                </div>
            </div>
        </div>

        <hr />

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
                <FontAwesomeIcon :icon="faDownload" class="text-primary q-ml-lg" style="font-size: 48px" />
            </div>
        </div>

        <hr />

        <div class="info-section q-py-lg">
            <div class="row items-start">
                <FontAwesomeIcon :icon="faUpload" class="text-primary q-mr-lg" style="font-size: 48px" />
                <div class="info-text">
                    <div class="text-h6 text-weight-bold">Publish</div>
                    <div class="text-body1">
                        Share your tools with the community using
                        <a href="https://planemo.readthedocs.io/en/latest/publishing.html" target="_blank">Planemo</a>.
                    </div>
                </div>
            </div>
        </div>

        <hr />

        <div class="info-section q-py-lg">
            <div class="row items-start justify-end">
                <div class="info-text text-right">
                    <div class="text-h6 text-weight-bold">Cite</div>
                    <div class="text-body1">
                        Information on citing the Tool Shed is available on the
                        <a href="https://galaxyproject.org/citing-galaxy/#toolshed" target="_blank">Galaxy Hub</a>.
                    </div>
                </div>
                <FontAwesomeIcon :icon="faQuoteLeft" class="text-primary q-ml-lg" style="font-size: 48px" />
            </div>
        </div>
    </div>
</template>

<style scoped>
.info-text {
    max-width: 280px;
}
</style>
