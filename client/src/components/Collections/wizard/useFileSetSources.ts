import { type Ref, ref } from "vue";

import { getRemoteEntriesAt } from "@/components/Upload/utils";

import { type ListUriResponse, type RemoteDirectory, type RemoteFile } from "./types";

export function useFileSetSources(isBusy: Ref<boolean>) {
    const pasteData = ref<string[][]>([] as string[][]);
    const tabularDatasetContents = ref<string[][]>([] as string[][]);
    const uris = ref<RemoteFile[]>([]);

    async function setRemoteFilesFolder(uri: string) {
        isBusy.value = true;
        const rawFiles = await getRemoteEntriesAt(uri);
        if (rawFiles) {
            const files: RemoteFile[] = (rawFiles as ListUriResponse).filter(
                (file: RemoteFile | RemoteDirectory) => file["class"] == "File"
            ) as RemoteFile[];
            uris.value = files;
        }
        isBusy.value = false;
    }

    async function onFtp() {
        setRemoteFilesFolder("gxftp://");
    }

    function setDatasetContents(contents: string[][]) {
        tabularDatasetContents.value = contents;
    }

    function setPasteTable(newValue: string[][]) {
        pasteData.value = newValue;
    }

    return {
        pasteData,
        tabularDatasetContents,
        uris,
        setRemoteFilesFolder,
        onFtp,
        setDatasetContents,
        setPasteTable,
    };
}
