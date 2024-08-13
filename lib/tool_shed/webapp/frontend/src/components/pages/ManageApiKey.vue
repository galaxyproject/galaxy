<script setup lang="ts">
import { ref, computed } from "vue"
import PageContainer from "@/components/PageContainer.vue"
import { ToolShedApi } from "@/schema"
import { notify, copyAndNotify, notifyOnCatch } from "@/util"
import ConfigFileContents from "@/components/ConfigFileContents.vue"

const apiKey = ref<string | null>(null)
const planemoConfig = computed(
    () =>
        `sheds:
  toolshed:
    key: ${apiKey.value}`
)

async function copyKey() {
    if (apiKey.value) {
        copyAndNotify(apiKey.value, "API key copied to your clipboard")
    }
}

const params = { encoded_user_id: "current" }

async function init() {
    const { data, error } = await ToolShedApi().GET("/api/users/{encoded_user_id}/api_key", {
        params: {
            path: params,
        },
    })

    if (error) {
        notifyOnCatch(new Error(`Error fetching API key: ${error.err_msg}`))
        return
    }

    apiKey.value = data
}

async function deleteKey() {
    const { error } = await ToolShedApi().DELETE("/api/users/{encoded_user_id}/api_key", {
        params: {
            path: params,
        },
    })

    if (error) {
        notifyOnCatch(new Error(`Error deactivating API key: ${error.err_msg}`))
        return
    }

    apiKey.value = null
    notify("API key deactivated")
}

async function recreateKey() {
    const { data, error } = await ToolShedApi().POST("/api/users/{encoded_user_id}/api_key", {
        params: {
            path: params,
        },
    })

    if (error) {
        notifyOnCatch(new Error(`Error re-generating API key: ${error.err_msg}`))
        return
    }

    apiKey.value = data
    notify("Re-generated API key")
}

void init()
</script>
<template>
    <page-container>
        Your API Key.
        <div>
            <q-input class="q-pa-lg" v-model="apiKey" readonly filled style="max-width: 450px">
                <template #append>
                    <q-avatar>
                        <q-btn flat dense icon="content_copy" @click="copyKey" />
                    </q-avatar>
                    <q-avatar>
                        <q-btn flat dense icon="delete" @click="deleteKey" />
                    </q-avatar>
                    <q-avatar>
                        <q-btn flat dense icon="refresh" @click="recreateKey" />
                    </q-avatar>
                </template>
            </q-input>
        </div>
        <p>
            This API key will allow you to access the Tool Shed via its web API. Please note that this key acts as an
            alternate means to access your account and should be treated with the same care as your login password.
        </p>
        <p>
            Add the following block to your Planemo configuration file (typically) found in
            <code>~/.planemo.yml</code> in your
        </p>
        <config-file-contents name=".planemo.yml" :contents="planemoConfig" what="Planemo configuration" />
    </page-container>
</template>
