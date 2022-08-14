<template>
    <div>
        <h1>About This Galaxy</h1>
        <p>This is an about page</p>
        <ConfigProvider v-slot="{ config }">
            <p>Config: {{ config }}</p>
            <!-- 
                Current version, including minor, and extra tags.
                Terms URL
                Help URL
            -->
        </ConfigProvider>
    </div>
</template>

<script setup lang="ts">
import ConfigProvider from "components/providers/ConfigProvider";
</script>

<style scoped>

</style>