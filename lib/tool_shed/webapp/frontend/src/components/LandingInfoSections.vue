<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faDownload, faMagnifyingGlass, faQuoteLeft, faUpload } from "@fortawesome/free-solid-svg-icons"
import { RouterLink } from "vue-router"
</script>
<template>
    <div class="landing-info-sections">
        <div class="info-section">
            <div class="info-row">
                <FontAwesomeIcon :icon="faMagnifyingGlass" class="info-icon" style="font-size: 48px" />
                <div class="info-text">
                    <h2 class="info-heading">Find</h2>
                    <div>
                        <router-link to="/repositories_by_category">Browse repositories by category</router-link> or
                        <router-link to="/repositories_by_owner">by owner</router-link>.
                    </div>
                </div>
            </div>
        </div>

        <hr />

        <div class="info-section">
            <div class="info-row info-row-end">
                <div class="info-text info-text-right">
                    <h2 class="info-heading">Install</h2>
                    <div>
                        Learn how to install tools in Galaxy from the
                        <a
                            href="https://training.galaxyproject.org/training-material/topics/admin/tutorials/tool-management/tutorial.html"
                            target="_blank"
                            >Galaxy Training Network tutorial</a
                        >.
                    </div>
                </div>
                <FontAwesomeIcon :icon="faDownload" class="info-icon info-icon-end" style="font-size: 48px" />
            </div>
        </div>

        <hr />

        <div class="info-section">
            <div class="info-row">
                <FontAwesomeIcon :icon="faUpload" class="info-icon" style="font-size: 48px" />
                <div class="info-text">
                    <h2 class="info-heading">Publish</h2>
                    <div>
                        Share your tools with the community using
                        <a href="https://planemo.readthedocs.io/en/latest/publishing.html" target="_blank">Planemo</a>.
                    </div>
                </div>
            </div>
        </div>

        <hr />

        <div class="info-section">
            <div class="info-row info-row-end">
                <div class="info-text info-text-right">
                    <h2 class="info-heading">Cite</h2>
                    <div>
                        Information on citing the Tool Shed is available on the
                        <a href="https://galaxyproject.org/citing-galaxy/#toolshed" target="_blank">Galaxy Hub</a>.
                    </div>
                </div>
                <FontAwesomeIcon :icon="faQuoteLeft" class="info-icon info-icon-end" style="font-size: 48px" />
            </div>
        </div>
    </div>
</template>

<style scoped>
.info-section {
    padding-top: var(--spacing-6);
    padding-bottom: var(--spacing-6);
}

.info-row {
    display: flex;
    align-items: flex-start;
}

.info-row-end {
    justify-content: flex-end;
}

.info-icon {
    color: var(--color-galaxy-primary);
    margin-right: var(--spacing-6);
}

.info-icon-end {
    margin-right: 0;
    margin-left: var(--spacing-6);
}

.info-text {
    max-width: 280px;
    /* Quasar's text-body1, which this text carried */
    font-size: 1rem;
    line-height: 1.5;
}

.info-text-right {
    text-align: right;
}

.info-heading {
    margin: 0;
    font-size: 1.25rem;
    font-weight: bold;
}
</style>
