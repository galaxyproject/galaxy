import { reactive, ref } from "vue";

export interface PyodideFile {
    id: string;
    url: string;
    name?: string;
    size?: number;
    aliases?: string[];
    mime_type?: string;
}

export interface PyodideTask {
    task_id?: string;
    code: string;
    packages?: string[];
    files?: PyodideFile[];
    timeout_ms?: number;
    alias_map?: Record<string, string>;
    config?: {
        index_url?: string;
    };
}

export interface PyodideArtifact {
    name?: string;
    path?: string;
    size?: number;
    mime_type?: string;
    buffer?: ArrayBuffer;
    dataset_id?: string;
    download_url?: string;
}

export interface PyodideRunResult {
    success: boolean;
    stdout: string;
    stderr: string;
    artifacts?: PyodideArtifact[];
    stats?: Record<string, unknown>;
    error?: string;
}

export interface PyodideStatusEvent {
    status: string;
    [key: string]: unknown;
}

interface RunnerHooks {
    onStdout?: (text: string) => void;
    onStderr?: (text: string) => void;
    onStatus?: (event: PyodideStatusEvent) => void;
}

interface PendingRequest {
    resolve: (result: PyodideRunResult) => void;
    reject: (error: unknown) => void;
    hooks: RunnerHooks;
}

const isSupported = ref(
    typeof window !== "undefined" && typeof Worker !== "undefined" && typeof WebAssembly !== "undefined",
);
const isRunning = ref(false);

let worker: Worker | null = null;
const pending = reactive(new Map<string, PendingRequest>());

function ensureWorker(): Worker {
    if (!isSupported.value) {
        throw new Error("Pyodide is not supported in this environment");
    }
    if (!worker) {
        worker = new Worker(new URL("../components/ChatGXY/pyodide.worker.ts", import.meta.url));
        worker.onmessage = (event: MessageEvent) => {
            const { type, id } = event.data as { type: string; id: string };
            if (!id) {
                return;
            }
            const entry = pending.get(id);
            if (!entry) {
                return;
            }
            if (type === "stdout" && entry.hooks.onStdout) {
                entry.hooks.onStdout((event.data as { text: string }).text);
            } else if (type === "stderr" && entry.hooks.onStderr) {
                entry.hooks.onStderr((event.data as { text: string }).text);
            } else if (type === "status" && entry.hooks.onStatus) {
                entry.hooks.onStatus(event.data as PyodideStatusEvent);
            } else if (type === "result") {
                pending.delete(id);
                const resultPayload = (event.data as { result: PyodideRunResult & { artifacts?: any[] } }).result;
                if (Array.isArray(resultPayload.artifacts)) {
                    resultPayload.artifacts = resultPayload.artifacts.map((artifact: any) => {
                        const buffer = artifact.binary as ArrayBuffer | undefined;
                        if (buffer) {
                            artifact.buffer = buffer;
                        }
                        delete artifact.binary;
                        return artifact as PyodideArtifact;
                    });
                }
                entry.resolve(resultPayload);
                isRunning.value = pending.size > 0;
            } else if (type === "error") {
                pending.delete(id);
                const payload = event.data as { error: string; stdout?: string; stderr?: string };
                const error = new Error(payload.error);
                (error as any).stdout = payload.stdout;
                (error as any).stderr = payload.stderr;
                entry.reject(error);
                isRunning.value = pending.size > 0;
            }
        };
        worker.onerror = (event) => {
            pending.forEach((entry) => {
                entry.reject(event);
            });
            pending.clear();
            isRunning.value = false;
        };
    }
    return worker;
}

export function usePyodideRunner() {
    async function runTask(task: PyodideTask, hooks: RunnerHooks = {}): Promise<PyodideRunResult> {
        const workerInstance = ensureWorker();
        const taskId = task.task_id ?? `pyodide-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
        const payload: PyodideTask = {
            ...task,
            task_id: taskId,
        };

        return new Promise<PyodideRunResult>((resolve, reject) => {
            pending.set(taskId, { resolve, reject, hooks });
            isRunning.value = true;
            workerInstance.postMessage({ type: "execute", id: taskId, task: payload });
        });
    }

    return {
        runTask,
        isSupported,
        isRunning,
    };
}
