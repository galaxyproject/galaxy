<script setup lang="ts">
import { faSlidersH } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useRouter } from "vue-router/composables";

import { useGlobalUploadModal } from "@/composables/globalUploadModal";

import GButton from "@/components/BaseComponents/GButton.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";

const router = useRouter();
const { openGlobalUploadModal } = useGlobalUploadModal();

const breadcrumbItems = [{ title: "Import Data", to: "/upload" }, { title: "Advanced Import" }];

function cancel() {
    router.push("/upload");
}

function openLegacyUpload() {
    openGlobalUploadModal();
}
</script>

<template>
    <div class="upload-advanced-view d-flex flex-column h-100">
        <BreadcrumbHeading :items="breadcrumbItems">
            <template v-slot:icon>
                <FontAwesomeIcon :icon="faSlidersH" class="mr-1" />
            </template>
        </BreadcrumbHeading>

        <div class="flex-grow-1 overflow-auto p-3">
            <div class="advanced-import-content">
                <h4>Advanced Import - Under Development 🚧</h4>
                <p>
                    For complex data import scenarios including composite files, rule-based transformations, and
                    advanced metadata management.
                </p>

                <div class="mt-4">
                    <p class="text-muted">
                        This mode is designed for advanced users who need more control over the import process,
                        including handling complex file structures and applying sophisticated data organization rules.
                    </p>

                    <!-- Placeholder content -->
                    <div class="advanced-features-placeholder border rounded p-4 mt-3">
                        <p><strong>Advanced Import Features:</strong></p>
                        <ul>
                            <li>
                                <strong>Composite Files:</strong> Import files with multiple components that should be
                                treated as a single dataset (e.g., HTML files with images, BAM files with indexes)
                            </li>
                            <li>
                                <strong>Rule Builder:</strong> Apply complex rules to parse filenames, extract metadata,
                                and organize data into collections automatically
                            </li>
                            <li>
                                <strong>Multi-source Import:</strong> Combine data from multiple sources (local files,
                                URLs, remote files) in a single import operation
                            </li>
                        </ul>

                        <div class="mt-4 p-3 border-top">
                            <p class="mb-2">
                                <strong>Need to use advanced features now?</strong>
                            </p>
                            <p class="text-muted small mb-2">
                                While we're developing this new interface, you can access the current upload dialog
                                which includes composite files, rule builder, and collection creation features.
                            </p>
                            <GButton variant="primary" @click="openLegacyUpload"> Open Current Upload Dialog </GButton>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="border-top p-3 d-flex justify-content-end">
            <GButton variant="secondary" @click="cancel"> Back to Upload Methods </GButton>
        </div>
    </div>
</template>

<style lang="scss" scoped>
.upload-advanced-view {
    background: var(--masthead-bg);
}

.advanced-import-content {
    max-width: 1200px;
    margin: 0 auto;
}

.advanced-features-placeholder {
    background: var(--masthead-bg-secondary, #f8f9fa);
}
</style>
