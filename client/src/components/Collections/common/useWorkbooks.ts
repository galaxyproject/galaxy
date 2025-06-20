import { faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

import { errorMessageAsString } from "@/utils/simple-error";

import HiddenWorkbookUploadInput from "@/components/Collections/wizard/HiddenWorkbookUploadInput.vue";

export const fileToBase64 = (file: File): Promise<string> =>
    new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = (error) => reject(error);
        reader.readAsDataURL(file);
    });

export type WorkbookHandler = (workbookContentBase64: string) => Promise<void>;

export function useWorkbookDropHandling(workbookHandler: WorkbookHandler) {
    const uploadErrorMessage = ref<string | undefined>(undefined);
    const isDragging = ref(false);
    const isProcessingUpload = ref(false);

    async function onFileUpload(event: Event) {
        const input = event.target as HTMLInputElement;
        const file = input.files?.[0] ?? null;
        if (file) {
            if (file.size > 10 * 1024 * 1024) {
                // Limit to 10MB
                uploadErrorMessage.value = "File size exceeds 10MB limit.";
                return;
            }
            const base64Content = await readAsBase64(file);
            workbookHandler(base64Content);
        }
    }

    async function readAsBase64(file: File) {
        const fileContent = await fileToBase64(file);
        const base64Content = fileContent.split(",")[1] as string;
        return base64Content;
    }

    function checkDrop(event: DragEvent): File | undefined {
        const file = event.dataTransfer?.files[0];
        if (!file || !file.name.endsWith(".xlsx")) {
            uploadErrorMessage.value = "Please drop a valid XLSX file.";
            return undefined;
        }
        return file;
    }

    const handleDrop = async (event: DragEvent) => {
        const file = checkDrop(event);
        if (!file) {
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            // Limit to 10MB
            uploadErrorMessage.value = "File size exceeds 10MB limit.";
            return;
        }

        isDragging.value = false;
        isProcessingUpload.value = true;
        try {
            // Read and base64 encode the file
            const base64Content = await readAsBase64(file);
            await workbookHandler(base64Content);
        } catch (error) {
            console.error("Error uploading file:", error);
            uploadErrorMessage.value = "Error processing the file: " + errorMessageAsString(error);
        } finally {
            isProcessingUpload.value = false;
        }
    };

    const uploadRef = ref<InstanceType<typeof HiddenWorkbookUploadInput>>();

    interface HasBrowse {
        browse: () => void;
    }

    function browseFiles() {
        const ref = uploadRef.value;
        if (ref) {
            (ref as unknown as HasBrowse).browse();
        }
    }

    const dropZoneClasses = computed(() => {
        const classes = ["dropzone"];
        if (isDragging.value) {
            classes.push("highlight");
        }
        return classes;
    });

    return {
        browseFiles,
        dropZoneClasses,
        FontAwesomeIcon,
        faUpload,
        readAsBase64,
        isDragging,
        isProcessingUpload,
        handleDrop,
        HiddenWorkbookUploadInput,
        onFileUpload,
        uploadErrorMessage,
        uploadRef,
    };
}
