<template>
    <BRow class="ml-3 mb-1">
        <i class="pref-icon pt-1 fa fa-lg fa-broadcast-tower" />
        <div class="pref-content pr-1">
            <a id="beacon-settings" href="javascript:void(0)"><b v-b-modal.modal-beacon v-localize>管理信标</b></a>
            <div v-localize class="form-text text-muted">向信标贡献变异数据</div>
            <BModal
                id="modal-beacon"
                ref="modal"
                size="xl"
                ok-only
                title="管理信标"
                title-tag="h1"
                @show="onOpenModal">
                <!-- Explanation text-->
                <p>
                    <a href="https://beacon-project.io">全球基因组学与健康联盟信标项目</a>使安全共享人类基因变异成为可能。<br />
                    <br />
                    Galaxy允许您使用信标协议以下述匿名方式直接从您的分析中与科学界共享基因变异：<br />
                    <br />
                    对于参与的用户，我们将把要共享的变异列表合并到每个参考基因组的单个信标数据集中，并通过信标服务器使该数据集可访问。<br />
                    如果有人查询服务器中的特定变异，而该变异存在于我们的信标数据集中，服务器将回复
                    <span class="cursive">"是的，我们见过这样的变异"</span>。<br />
                    <br />
                    发出查询的用户随后可以联系Galaxy服务器管理员，管理员可以将相关变异调用链接到特定的Galaxy用户。如果您是共享该变异的用户之一，管理员将联系您，询问您是否愿意与发起查询的用户联系，以协商进一步的信息交流或数据访问。
                </p>

                <BAlert v-if="enabled" show>
                    <div class="flex-row space-between">
                        <div class="no-shrink">
                            信标共享已为您的个人资料<span class="bold">启用</span>
                        </div>
                        <div class="fill"></div>
                        <div class="no-shrink">
                            <BButton variant="danger" @click="optOut">禁用</BButton>
                        </div>
                    </div>
                </BAlert>

                <!-- Setting to show when beacon is disabled -->
                <BAlert v-if="!enabled" show>
                    <div class="flex-row space-between">
                        <div class="no-shrink">
                            信标共享当前<span class="bold">已禁用</span> - 不会共享任何数据
                        </div>
                        <div class="fill"></div>
                        <div>
                            <BButton variant="success" @click="optIn">启用</BButton>
                        </div>
                    </div>
                </BAlert>

                <div v-if="enabled">
                    <p>
                        您可以通过将VCF或VCF.bgzip文件复制到名为
                        <span class="cursive gray-background">{{ beaconHistoryName }}</span>的历史记录来共享数据。<br />
                        <br />
                        信标数据库会定期重建。因此，更改不会立即生效。如果您禁用信标共享或从信标历史记录中移除数据集，相应的变异将在下次重建期间从信标数据集中消失。
                    </p>
                </div>

                <!-- Detailed information about the beacon history -->
                <div v-if="enabled" class="gray-box">
                    <!-- Case: History does not exist-->
                    <div v-if="beaconHistories.length < 1" class="flex-row history-entry">
                        <div class="no-shrink">未找到信标历史记录</div>
                        <div class="fill"></div>
                        <div class="no-shrink">
                            <BButton @click="createBeaconHistory">创建信标历史记录</BButton>
                        </div>
                    </div>

                    <!-- Case: History exists -->
                    <div
                        v-for="beaconHistory in beaconHistories"
                        :key="beaconHistory.id"
                        class="flex-row history-entry"
                        :class="{
                            'gray-border-bottom': beaconHistory.id !== beaconHistories[beaconHistories.length - 1].id,
                        }">
                        <div v-if="beaconHistory.contents" class="no-shrink">
                            包含 {{ beaconHistory.contents.length }} 个数据集的历史记录
                        </div>
                        <div class="fill"></div>
                        <div class="no-shrink">
                            <BButton @click="switchHistory(beaconHistory.id)">切换到此历史记录</BButton>
                        </div>
                    </div>
                </div>

                <div v-if="enabled">
                    <p>数据集必须满足以下条件才能被处理</p>
                    <ul>
                        <li>必须为VCF或VCF.bgzip格式</li>
                        <li>必须分配有人类参考基因组（例如hg19）</li>
                        <li>必须在专用基因型列中定义至少一个样本</li>
                        <li>
                            必须包含信息字段 <span class="cursive">AC</span>，其中包含调用基因型中替代等位基因的总数
                        </li>
                    </ul>
                </div>
            </BModal>
        </div>
    </BRow>
</template>

<script>
import axios from "axios";
import { BAlert, BButton, BModal, BRow } from "bootstrap-vue";
import { mapActions } from "pinia";
import { withPrefix } from "utils/redirect";

import { useHistoryStore } from "@/stores/historyStore";

export default {
    components: { BButton, BModal, BRow, BAlert },
    props: {
        userId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            enabled: false,
            beaconHistoryName: "Beacon 导出 📡",
            beaconHistories: [{}],
        };
    },
    methods: {
        ...mapActions(useHistoryStore, ["setCurrentHistory"]),
        switchHistory: async function (historyId) {
            await this.setCurrentHistory(historyId);
        },
        getBeaconHistories: function () {
            axios
                .get(withPrefix("api/histories?&keys=id,contents&q=name&qv=" + encodeURI(this.beaconHistoryName)))
                .then((response) => {
                    this.beaconHistories = this.removeDeletedContents(response.data);
                })
                .catch((error) => {
                    console.log(error.response);
                });
        },
        removeDeletedContents: function (beaconHistories) {
            beaconHistories.forEach((beaconHistory) => {
                beaconHistory.contents.splice(
                    0,
                    beaconHistory.contents.length,
                    ...beaconHistory.contents.filter((dataset) => {
                        return !dataset.deleted;
                    })
                );
            });
            return beaconHistories;
        },
        createBeaconHistory: function () {
            const annotation =
                "Variants will be collected from VCF datasets in this history if beacon sharing is activated";
            axios
                .post(withPrefix("api/histories"), { name: this.beaconHistoryName })
                .then((response) => {
                    axios.put(withPrefix(`api/histories/${response.data.id}`), { annotation: annotation }).then(() => {
                        this.getBeaconHistories();
                    });
                })
                .catch((error) => {
                    this.errorMessages.push(error.response.data.err_msg), console.log(error.response);
                });
        },
        optIn() {
            try {
                axios.post(withPrefix(`api/users/${this.userId}/beacon`), { enabled: true }).then((response) => {
                    // TODO check response
                    this.loadSettings();
                    if (this.beaconHistories.length < 1) {
                        this.createBeaconHistory();
                        this.getBeaconHistories();
                    }
                });
            } catch (e) {
                console.log(e);
            }
        },
        optOut() {
            try {
                axios.post(withPrefix(`api/users/${this.userId}/beacon`), { enabled: false }).then((response) => {
                    // TODO check response
                    this.loadSettings();
                });
            } catch (e) {
                console.log(e);
            }
        },
        onOpenModal() {
            this.loadSettings();
            this.getBeaconHistories();
        },
        async loadSettings() {
            try {
                await axios.get(withPrefix(`api/users/${this.userId}/beacon`)).then((response) => {
                    this.enabled = response.data.enabled;
                });
            } catch (e) {
                console.log(e);
            }
        },
    },
};
</script>

<style scoped>
span.bold {
    font-weight: bold;
}

.pref-icon {
    width: 3rem;
}

.gray-box {
    margin-top: 32px;
    margin-bottom: 32px;
    border: 1px solid #bdc6d0;
    border-radius: 5px;
    background-color: rgba(0, 0, 0, 0.04);
}

.flex-row {
    display: flex;
    flex-flow: row;
}

.history-entry {
    padding: 8px;
}

.gray-border-bottom {
    border-bottom: 1px solid #bdc6d0;
}

.space-between {
    justify-content: space-between;
    align-items: center;
}

.cursive {
    font-style: italic;
}

.bold {
    font-weight: bolder;
}

.fill {
    width: 100%;
}

.no-shrink {
    flex-shrink: 0;
}
</style>
