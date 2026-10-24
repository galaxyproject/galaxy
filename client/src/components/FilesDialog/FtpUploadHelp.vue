<script setup lang="ts">
import { useConfig } from "@/composables/config";

import GAlert from "@/components/BaseComponents/GAlert.vue";

defineProps<{
    /** Shown only when this is the FTP directory's URI. */
    uri?: string;
}>();

const { config, isConfigLoaded } = useConfig();
</script>

<template>
    <GAlert v-if="isConfigLoaded && uri === 'gxftp://'" variant="info" show data-description="ftp upload help">
        This Galaxy server allows you to upload files via FTP. To upload some files, log in to the FTP server at
        <strong>{{ config.ftp_upload_site }}</strong> using your Galaxy credentials. For help visit the
        <a href="https://galaxyproject.org/ftp-upload/" target="_blank">tutorial</a>.
        <span v-if="config.enable_oidc"
            ><br />If you are signed-in to Galaxy using a third-party identity and you
            <strong>do not have a Galaxy password</strong> please use the reset password option in the login form with
            your email to create a password for your account.</span
        >
    </GAlert>
</template>
