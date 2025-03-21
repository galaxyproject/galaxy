<!--
    WARNING
    This component is temporal and should be dropped once Celery is the default task system in Galaxy.
    The plugin system should be used instead.
-->
<template>
    <div>
        <p>
            BioCompute 对象 (BCO) 是遵循
            <a href="https://standards.ieee.org/ieee/2791/7337/">IEEE-2791-2020 标准</a> 的 JSON 对象的非官方名称。 
            BCO 旨在传达高通量测序 (HTS) 分析结果、数据集创建、数据管理和生物信息学验证协议。
        </p>
        <p>了解更多关于 <a href="https://biocomputeobject.org/" target="_blank">BioCompute 对象</a> 的信息。</p>
        <p>
            <a href="https://w3id.org/biocompute/tutorials/galaxy_quick_start" target="_blank"
                >使用 Galaxy 创建 BCO</a
            > 的说明。
        </p>
        <b-tabs lazy>
            <b-tab title="下载">
                <a class="bco-json" style="padding-left: 1em" :href="bcoDownloadLink"><b>下载 BCO</b></a>
            </b-tab>
            <b-tab title="提交到 BCODB">
                <div>
                    <p>
                        要提交到 BCODB，您需要已经拥有一个经过身份验证的账户。从 Galaxy 提交 BCO 的说明可在
                        <a href="https://w3id.org/biocompute/tutorials/galaxy_quick_start/" target="_blank">此处</a> 获取。
                    </p>
                    <form @submit.prevent="submitForm">
                        <div class="form-group">
                            <label for="fetch">
                                <input
                                    id="fetch"
                                    v-model="form.fetch"
                                    type="text"
                                    class="form-control"
                                    placeholder="https://biocomputeobject.org"
                                    autocomplete="off"
                                    required />
                                BCO DB URL (示例: https://biocomputeobject.org)
                            </label>
                        </div>
                        <div class="form-group">
                            <label for="authorization">
                                <input
                                    id="authorization"
                                    v-model="form.authorization"
                                    type="password"
                                    class="form-control"
                                    autocomplete="off"
                                    required />
                                用户 API 密钥
                            </label>
                        </div>
                        <div class="form-group">
                            <label for="table">
                                <input
                                    id="table"
                                    v-model="form.table"
                                    type="text"
                                    class="form-control"
                                    placeholder="GALXY"
                                    required />
                                前缀
                            </label>
                        </div>
                        <div class="form-group">
                            <label for="owner_group">
                                <input
                                    id="owner_group"
                                    v-model="form.owner_group"
                                    type="text"
                                    class="form-control"
                                    autocomplete="off"
                                    required />
                                用户名
                            </label>
                        </div>
                        <div class="form-group">
                            <button class="btn btn-primary">{{ "提交" | localize }}</button>
                        </div>
                    </form>
                </div>
            </b-tab>
        </b-tabs>
    </div>
</template>

<script>
import axios from "axios";
import { getRootFromIndexLink } from "onload";
import { getAppRoot } from "onload/loadConfig";

const getUrl = (path) => getRootFromIndexLink() + path;
export default {
    props: {
        invocationId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            form: {
                fetch: "",
                authorization: "",
                table: "",
                owner_group: "",
            },
        };
    },
    computed: {
        bcoDownloadLink: function () {
            return `${getAppRoot()}api/invocations/${this.invocationId}/biocompute/download`;
        },
    },
    methods: {
        async submitForm() {
            const bco = await axios
                .get(getUrl(`./api/invocations/${this.invocationId}/biocompute/`))
                .then((response) => {
                    this.bco = response.data;
                    return this.bco;
                })
                .catch((e) => {
                    this.errors.push(e);
                });
            const bcoString = {
                POST_api_objects_draft_create: [
                    {
                        contents: bco,
                        owner_group: this.form.owner_group,
                        schema: "IEEE",
                        prefix: this.form.table,
                    },
                ],
            };
            const headers = {
                Authorization: "Token " + this.form.authorization,
                "Content-type": "application/json; charset=UTF-8",
            };
            const submitURL = this.form.fetch;
            axios
                .post(`${submitURL}/api/objects/drafts/create/`, bcoString, { headers: headers })
                .then((response) => {
                    if (response.status === 200) {
                        console.log("response:", response);
                        alert(response.data[0].message);
                    }
                    if (response.status === 207) {
                        console.log("response:", response);
                        alert(response.data[0].message);
                    }
                })
                .catch(function (error) {
                    console.log("Error", { ...error });
                    if (error.response.status == 401) {
                        alert(error.response.data.detail);
                        console.log("Error response: ", error);
                    } else {
                        console.log("Error", error);
                        alert("Error", error);
                    }
                });
            this.form.owner_group = "";
            this.form.authorization = "";
            this.form.owner_group = "";
            this.form.fetch = "";
        },
    },
};
</script>
