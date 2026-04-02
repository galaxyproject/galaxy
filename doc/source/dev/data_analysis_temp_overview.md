# Galaxy Data Analysis Agent — Temporary Implementation Notes

These notes capture the current state of the DSPy-powered data analysis agent and how it interacts with the ChatGXY frontend. They are intentionally lightweight so we can iterate quickly; fold them into permanent docs once the flow settles.

## Backend (Python / Galaxy)

1. **Agent Class**: `lib/galaxy/agents/data_analysis.py` hosts `DataAnalysisAgent`, which turns user prompts into execution plans via DSPy (`GalaxyDSPyPlanner`). The system prompt now explicitly requires code to save artifacts inside `generated_file/` and to print short summaries plus the relative paths for every generated artifact.

2. **Planner / Tools**: `lib/galaxy/agents/dspy_adapter.py` wires DSPy’s ReAct/CodeReact modules to our dataset lookup + code capture tools. The planner captures the emitted Python and requirements, then hands them to the Pyodide executor via metadata on the agent response.

3. **Execution Tracking**:
   * Each message that contains `metadata.pyodide_task` triggers a Pyodide task on the client. Once it completes, the browser POSTs `/api/chat/exchange/<id>/pyodide_result` (see `lib/galaxy/webapps/galaxy/api/chat.py`), which creates a new message storing stdout/stderr plus any artifacts.
   * Artifacts are uploaded via `/api/chat/exchange/<id>/artifacts`, which stores them in the user’s history but associates them with the chat exchange for UI display.

4. **Failure Handling**: When the generated code raises an error, the execution result records the traceback, so the agent can decide whether to regenerate code or surface the failure. A recent change also forces Pyodide to run `ast.parse` on the code before executing it, so syntax issues (e.g., unterminated strings) are caught immediately and reported clearly.

## Frontend (ChatGXY Vue app)

1. **Dataset Selection**: ChatGXY lets users pick datasets; their encoded IDs flow through `context.dataset_ids` so the agent knows what to load. We also support natural-language lookup through the DSPy `dataset_lookup` tool.

2. **Pyodide Execution Loop**:
   * `client/src/composables/usePyodideRunner.ts` posts tasks to `pyodide.worker.ts` (a dedicated Web Worker). The worker sets up `/data` and `/tmp/galaxy/outputs_dir/generated_file` and mirrors the outputs to `generated_file/` so they can be uploaded.
   * Before running user code, the worker now runs `ast.parse` to catch syntax errors. After execution it enumerates new files and appends either the captured scalar summaries or a “generated_files = [...]” line to stdout, ensuring the backend always gets a non-empty observation.

3. **Artifact Display**: When the browser uploads artifacts, ChatGXY renders them under the relevant assistant message. Image MIME types get inline previews; other files show as download buttons with size info.

4. **Refresh / Retry Behavior**: The UI replays whatever the backend has stored. If the backend never records a successful `execution_result` (e.g., code threw an error or the server was offline when posting results), the planner still sees an “action pending” and will regenerate code once the user sends another message. With the stdout + artifact reporting improvements, successful runs no longer retrigger after a refresh.

## Generated Artifacts

* **Pyodide worker sandbox**: `client/src/components/ChatGXY/pyodide.worker.ts` mounts `/tmp/galaxy/outputs_dir` and always writes user artifacts inside `/tmp/galaxy/outputs_dir/generated_file`. A `generated_file/` symlink is also created at the sandbox root so the relative paths printed in stdout match what the backend expects.
* **Uploaded datasets**: When the browser POSTs `/api/chat/exchange/<id>/artifacts`, the bytes are written into the current history as standard HDAs. On disk they land in the configured object store (e.g., `database/objects/<sharding>/dataset_<id>.dat` for the default). You can inspect them from the History panel or by opening the dataset file path reported in the server logs.
* **Collection grouping**: If multiple artifacts are produced for a single query, the API automatically creates a hidden history dataset collection so the History panel shows a tidy bundle labelled after the user’s prompt.

## Known Pain Points / Next Steps

1. **Code Quality**: The LLM still occasionally emits malformed Python (unterminated strings). The new AST guard helps, but we should keep pushing prompt tweaks or add a server-side sanitizer.
2. **Error UX**: When the backend is unreachable (`/pyodide_result` proxy error), the agent currently retries. We may want a “do not auto retry failed actions” flag or a user-visible status that lets them choose to rerun.
3. **Documentation Debt**: Merge these notes into the permanent developer docs once the flow stabilizes so future contributors understand how ChatGXY + Pyodide + DSPy fit together.
