/// <reference lib="webworker" />

import { createWorkerErrorPayload, type ExecuteMessage, executePyodideTask } from "./pyodideRuntime";

const ctx: DedicatedWorkerGlobalScope = self as unknown as DedicatedWorkerGlobalScope;

ctx.addEventListener("message", (event: MessageEvent<ExecuteMessage>) => {
    const message = event.data;
    if (!message || message.type !== "execute") {
        return;
    }
    executePyodideTask(message).catch((err) => {
        ctx.postMessage(createWorkerErrorPayload(message.id, err));
    });
});
