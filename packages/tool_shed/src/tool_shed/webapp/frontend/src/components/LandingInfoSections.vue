<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faDownload, faMagnifyingGlass, faQuoteLeft, faUpload } from "@fortawesome/free-solid-svg-icons"
import { RouterLink } from "vue-router"
</script>
<template>
    <div class="landing-info-sections">
        <section class="info-section shed-card">
            <span class="info-icon" aria-hidden="true"><FontAwesomeIcon :icon="faMagnifyingGlass" /></span>
            <h2 class="info-heading">Find</h2>
            <p class="info-text">
                <router-link to="/repositories_by_category">Browse repositories by category</router-link> or
                <router-link to="/repositories_by_owner">by owner</router-link>.
            </p>
        </section>

        <section class="info-section shed-card">
            <span class="info-icon" aria-hidden="true"><FontAwesomeIcon :icon="faDownload" /></span>
            <h2 class="info-heading">Install</h2>
            <p class="info-text">
                Learn how to install tools in Galaxy from the
                <a
                    href="https://training.galaxyproject.org/training-material/topics/admin/tutorials/tool-management/tutorial.html"
                    target="_blank"
                    >Galaxy Training Network tutorial</a
                >.
            </p>
        </section>

        <section class="info-section shed-card">
            <span class="info-icon" aria-hidden="true"><FontAwesomeIcon :icon="faUpload" /></span>
            <h2 class="info-heading">Publish</h2>
            <p class="info-text">
                Share your tools with the community using
                <a href="https://planemo.readthedocs.io/en/latest/publishing.html" target="_blank">Planemo</a>.
            </p>
        </section>

        <section class="info-section shed-card">
            <span class="info-icon" aria-hidden="true"><FontAwesomeIcon :icon="faQuoteLeft" /></span>
            <h2 class="info-heading">Cite</h2>
            <p class="info-text">
                Information on citing the Tool Shed is available on the
                <a href="https://galaxyproject.org/citing-galaxy/#toolshed" target="_blank">Galaxy Hub</a>.
            </p>
        </section>
    </div>
</template>

<style scoped>
.landing-info-sections {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
    gap: 1rem;
}

.info-section {
    position: relative;
    padding: 1.4rem 1.4rem 1.25rem;
    overflow: hidden;
    transition:
        box-shadow var(--shed-transition),
        transform var(--shed-transition);
}

/* The Hub's hover reveal: a gold bar slides in along the card's left edge */
.info-section::before {
    content: "";
    position: absolute;
    inset: 0 auto 0 0;
    width: 4px;
    background: var(--shed-gold);
    transform: scaleY(0);
    transform-origin: top;
    transition: transform var(--shed-transition);
}

.info-section:hover {
    box-shadow: var(--shed-shadow-md);
}

.info-section:hover::before {
    transform: scaleY(1);
}

.info-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2.75rem;
    height: 2.75rem;
    margin-bottom: 0.9rem;
    font-size: 1.15rem;
    color: var(--color-galaxy-primary, #25537b);
    background: var(--color-bay-of-many-100, #edf4fa);
    border-radius: 0.6rem;
}

.info-heading {
    margin: 0 0 0.35rem;
    font-size: 1.15rem;
    font-weight: 700;
}

.info-text {
    margin: 0;
    line-height: 1.55;
}
</style>
