<script setup lang="ts">
import { getUploadRootBreadcrumb } from "./uploadBreadcrumb";

import UploadMethodList from "./UploadMethodList.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";

const breadcrumbItems = [getUploadRootBreadcrumb()];
</script>

<template>
    <div class="upload-page h-100 d-flex flex-column">
        <BreadcrumbHeading :items="breadcrumbItems" />

        <div class="upload-page-content flex-grow-1 overflow-auto px-3 pt-3">
            <div class="mb-3">
                <h2 class="h-lg mb-2">Choose an Import Method</h2>
                <p class="text-muted">Select how you want to import data into Galaxy</p>
            </div>

            <UploadMethodList :in-panel="false" />
        </div>
    </div>
</template>
