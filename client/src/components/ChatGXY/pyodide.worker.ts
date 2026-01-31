/// <reference lib="webworker" />

export {};

type PyodideAliasMap = Record<string, string>;

type PyodideFile = {
    id: string;
    url: string;
    name?: string;
    size?: number;
    aliases?: string[];
    mime_type?: string;
};

type PyodideTask = {
    task_id?: string;
    code: string;
    packages?: string[];
    files?: PyodideFile[];
    timeout_ms?: number;
    alias_map?: PyodideAliasMap;
    config?: {
        index_url?: string;
    };
};

type ExecuteMessage = {
    type: "execute";
    id: string;
    task: PyodideTask;
};

type PyodideArtifact = {
    name?: string;
    path?: string;
    size?: number;
    mime_type?: string;
    binary?: ArrayBuffer;
};

type PyodideResultMessage = {
    type: "result";
    id: string;
    result: {
        success: boolean;
        stdout: string;
        stderr: string;
        artifacts: PyodideArtifact[];
        stats?: Record<string, unknown>;
        error?: string;
    };
};

type PyodideErrorMessage = {
    type: "error";
    id: string;
    error: string;
    stdout: string;
    stderr: string;
};

type StatusPayload = {
    type: "status";
    id: string;
    status: string;
    [key: string]: unknown;
};

type StdStreamMessage = {
    type: "stdout" | "stderr";
    id: string;
    text: string;
};

const ctx: DedicatedWorkerGlobalScope = self as unknown as DedicatedWorkerGlobalScope;

const DEFAULT_INDEX_URL = "https://cdn.jsdelivr.net/pyodide/v0.26.1/full";
const DATA_ROOT = "/data";
const OUTPUT_ROOT = "/tmp/galaxy/outputs_dir";

let pyodidePromise: Promise<any> | null = null;
let pyodide: any = null;
let currentIndexUrl: string | null = null;
let loadedPackages = new Set<string>();
let stdoutBuffer = "";
let stderrBuffer = "";

ctx.addEventListener("message", (event: MessageEvent<ExecuteMessage>) => {
    const message = event.data;
    if (!message || message.type !== "execute") {
        return;
    }
    executeTask(message).catch((err) => {
        const errorMessage = err instanceof Error ? err.message : String(err);
        const payload: PyodideErrorMessage = {
            type: "error",
            id: message.id,
            error: errorMessage,
            stdout: stdoutBuffer,
            stderr: stderrBuffer,
        };
        ctx.postMessage(payload);
    });
});

async function ensurePyodide(indexURL?: string): Promise<any> {
    const targetUrl = indexURL || currentIndexUrl || DEFAULT_INDEX_URL;
    if (!pyodidePromise || targetUrl !== currentIndexUrl) {
        currentIndexUrl = targetUrl;
        pyodidePromise = (async () => {
            if (!(self as any).loadPyodide) {
                self.importScripts(`${targetUrl}/pyodide.js`);
            } else if (targetUrl !== DEFAULT_INDEX_URL) {
                self.importScripts(`${targetUrl}/pyodide.js`);
            }
            stdoutBuffer = "";
            stderrBuffer = "";
            loadedPackages = new Set<string>();
            const instance = await (self as any).loadPyodide({
                indexURL: targetUrl,
                stdout: handleStdout,
                stderr: handleStderr,
            });
            return instance;
        })();
    }
    pyodide = await pyodidePromise;
    return pyodide;
}

function handleStdout(text: string) {
    stdoutBuffer += text;
    const payload: StdStreamMessage = { type: "stdout", id: currentTaskId, text };
    ctx.postMessage(payload);
}

function handleStderr(text: string) {
    stderrBuffer += text;
    const payload: StdStreamMessage = { type: "stderr", id: currentTaskId, text };
    ctx.postMessage(payload);
}

let currentTaskId = "";

async function executeTask(message: ExecuteMessage) {
    const { id, task } = message;
    currentTaskId = id;
    stdoutBuffer = "";
    stderrBuffer = "";

    const status = (statusMessage: string, extra: Record<string, unknown> = {}) => {
        const payload: StatusPayload = { type: "status", id, status: statusMessage, ...extra };
        ctx.postMessage(payload);
    };

    status("initialising");
    const py = await ensurePyodide(task.config?.index_url);
    prepareFileSystem(py);

    if (task.packages && task.packages.length > 0) {
        await installPackages(py, task.packages, id);
    }

    const datasetEntries = await prepareDatasets(py, task.files || [], id);
    const aliasMap = task.alias_map || buildAliasMap(datasetEntries);
    await seedPythonEnvironment(py, datasetEntries, aliasMap);

    status("executing");
    const start = performance.now();
    const runResult = await runUserCode(py, task.code);
    const execMs = performance.now() - start;

    status("collecting");
    const { artifacts, transferables } = await collectArtifacts(py);

    const resultPayload: PyodideResultMessage = {
        type: "result",
        id,
        result: {
            success: runResult.success,
            stdout: stdoutBuffer,
            stderr: stderrBuffer,
            artifacts,
            stats: {
                exec_ms: Math.round(execMs),
            },
            error: runResult.error,
        },
    };
    ctx.postMessage(resultPayload, transferables);

    cleanupDatasets(py, datasetEntries);
    currentTaskId = "";
}

async function installPackages(py: any, packages: string[], id: string) {
    const missing = packages.filter((pkg) => pkg && !loadedPackages.has(pkg));
    if (missing.length === 0) {
        return;
    }
    const payload: StatusPayload = { type: "status", id, status: "installing", packages: missing };
    ctx.postMessage(payload);

    const micropipTargets: string[] = [];
    for (const pkg of missing) {
        try {
            await py.loadPackage(pkg);
            loadedPackages.add(pkg);
        } catch (err) {
            micropipTargets.push(pkg);
        }
    }

    if (micropipTargets.length === 0) {
        return;
    }

    try {
        await py.loadPackage("micropip");
    } catch (err) {
        // Ignore if already available
    }
    await py.runPythonAsync("import micropip");
    const jsonPackages = JSON.stringify(micropipTargets);
    await py.runPythonAsync(`import micropip\nawait micropip.install(${jsonPackages})`);
    micropipTargets.forEach((pkg) => loadedPackages.add(pkg));
}

function prepareFileSystem(py: any) {
    try {
        py.FS.mkdirTree(DATA_ROOT);
    } catch (err) {
        // ignore errors when directory already exists
    }
    try {
        py.FS.mkdirTree(OUTPUT_ROOT);
    } catch (err) {
        // ignore errors when directory already exists
    }
    clearDirectory(py, DATA_ROOT);
    clearDirectory(py, OUTPUT_ROOT);
}

async function prepareDatasets(py: any, files: PyodideFile[], id: string) {
    const usedNames = new Set<string>();
    const entries: Array<{ id: string; name: string; path: string; size: number; aliases: string[] }> = [];
    for (const file of files) {
        const statusPayload: StatusPayload = { type: "status", id, status: "fetch", file: file.id };
        ctx.postMessage(statusPayload);
        const response = await fetch(file.url, { credentials: "include" });
        if (!response.ok) {
            throw new Error(`Failed to fetch dataset ${file.name || file.id || "unknown"}`);
        }
        const buffer = await response.arrayBuffer();
        const view = new Uint8Array(buffer);
        let filename = sanitizeFilename(file.id || file.name || `dataset_${entries.length + 1}`);
        if (usedNames.has(filename)) {
            let counter = 1;
            while (usedNames.has(`${filename}_${counter}`)) {
                counter += 1;
            }
            filename = `${filename}_${counter}`;
        }
        usedNames.add(filename);
        let targetPath = `${DATA_ROOT}/${filename}`;
        let suffix = 1;
        while (fileExists(py, targetPath)) {
            targetPath = `${DATA_ROOT}/${filename}_${suffix}`;
            suffix += 1;
        }
        py.FS.writeFile(targetPath, view);
        entries.push({
            id: file.id,
            name: file.name || filename,
            path: targetPath,
            size: buffer.byteLength,
            aliases: uniqueAliases([file.id, file.name, filename, ...(file.aliases || [])]),
        });
    }
    return entries;
}

function fileExists(py: any, path: string): boolean {
    try {
        py.FS.stat(path);
        return true;
    } catch (err) {
        return false;
    }
}

async function seedPythonEnvironment(
    py: any,
    datasets: Array<{ id: string; name: string; path: string; size: number; aliases: string[] }>,
    aliasMap: PyodideAliasMap,
) {
    const datasetJson = JSON.stringify(datasets);
    const aliasJson = JSON.stringify(aliasMap);
    py.globals.set("_GXY_DATASETS_JSON", datasetJson);
    py.globals.set("_GXY_ALIAS_JSON", aliasJson);
    await py.runPythonAsync(
        `import json\nfrom pathlib import Path\nimport builtins as _gxy_builtins\nimport warnings as _gxy_warnings\n\ntry:\n    _gxy_warnings.filterwarnings(\n        "ignore",\n        message="Pyarrow will become a required dependency of pandas.*",\n        category=DeprecationWarning,\n    )\nexcept Exception:\n    pass\n\ntry:\n    _DATASET_ENTRIES = json.loads(globals().pop("_GXY_DATASETS_JSON"))\nexcept KeyError:\n    _DATASET_ENTRIES = []\n\ntry:\n    globals().pop("_GXY_ALIAS_JSON")\nexcept KeyError:\n    pass\n\n_DATASET_INDEX = {}\nfor entry in _DATASET_ENTRIES:\n    aliases = entry.get("aliases") or []\n    for alias in aliases:\n        if alias:\n            _DATASET_INDEX[alias] = entry\n    dataset_id = entry.get("id")\n    if dataset_id:\n        _DATASET_INDEX.setdefault(dataset_id, entry)\n\noutputs_root = Path("/tmp/galaxy")\noutputs_dir = outputs_root / "outputs_dir"\noutputs_dir.mkdir(parents=True, exist_ok=True)\ngenerated_dir = outputs_dir / "generated_file"\ngenerated_dir.mkdir(parents=True, exist_ok=True)\n\nalias_dir = Path("generated_file")\nif not alias_dir.exists():\n    try:\n        alias_dir.symlink_to(generated_dir)\n    except Exception:\n        if not alias_dir.exists():\n            alias_dir.mkdir(parents=True, exist_ok=True)\n\n_original_open = globals().get("_GXY_ORIGINAL_OPEN")\nif _original_open is None:\n    _original_open = _gxy_builtins.open\n    globals()[\"_GXY_ORIGINAL_OPEN\"] = _original_open\n\n\ndef _resolve_dataset(alias: str):\n    key = alias or \"\"\n    entry = _DATASET_INDEX.get(key)\n    if entry is None:\n        raise KeyError(f\"Unknown dataset alias: {alias}\")\n    return entry\n\ndef get_dataset_path(alias: str) -> str:\n    return _resolve_dataset(alias)[\"path\"]\n\ndef load_dataset(alias: str, **read_kwargs):\n    entry = _resolve_dataset(alias)\n    path = entry[\"path\"]\n    import pandas as pd\n    name = entry.get(\"name\") or \"\"\n    if not read_kwargs and (name.lower().endswith(\".tsv\") or path.lower().endswith(\".tsv\")):\n        read_kwargs.setdefault(\"sep\", \"\\t\")\n    return pd.read_csv(path, **read_kwargs)\n\ndef _open_with_alias(path, *args, **kwargs):\n    if isinstance(path, str) and path in _DATASET_INDEX:\n        return _original_open(_DATASET_INDEX[path][\"path\"], *args, **kwargs)\n    return _original_open(path, *args, **kwargs)\n\n_gxy_builtins.open = _open_with_alias\n\nglobals()[\"_GXY_ORIGINAL_LOAD_DATASET\"] = load_dataset\nglobals()[\"_GXY_ORIGINAL_GET_DATASET_PATH\"] = get_dataset_path\nimport os as _gxy_os\n_gxy_os.environ.setdefault("MPLBACKEND", "agg")\ntry:\n    import matplotlib\n    matplotlib.use(\"agg\")\nexcept Exception:\n    pass\n\n# Ensure relative file writes land inside the artifact directory.\ntry:\n    _gxy_os.chdir(str(outputs_dir))\nexcept Exception:\n    pass\n`,
    );
}

async function runUserCode(py: any, code: string): Promise<{ success: boolean; error?: string }> {
    if (!code || !code.trim()) {
        return { success: true };
    }
    await py.runPythonAsync("_GXY_PRE_KEYS = set(globals().keys())");
    try {
        try {
            await py.runPythonAsync("import matplotlib\nmatplotlib.use('agg')");
        } catch (error) {
            // Ignore backend configuration errors
        }

        py.globals.set("_GXY_USER_CODE", code);
        try {
            await py.runPythonAsync(
                [
                    "import ast",
                    "try:",
                    "    ast.parse(_GXY_USER_CODE)",
                    "except SyntaxError as exc:",
                    "    raise SyntaxError(f'Syntax error in generated code: {exc}')",
                ].join("\n"),
            );
        } finally {
            await py.runPythonAsync("globals().pop('_GXY_USER_CODE', None)");
        }

        const preArtifactsJson = await py.runPythonAsync(
            "import json, os\n" +
                "try:\n" +
                "    files = os.listdir('generated_file')\n" +
                "except Exception:\n" +
                "    files = []\n" +
                "json.dumps(sorted(files))\n",
        );
        const preArtifacts = new Set<string>(JSON.parse(preArtifactsJson));

        await py.runPythonAsync(code);

        const scalarSummary: string = await py.runPythonAsync(
            [
                "summary_lines = []",
                "pre_keys = globals().get('_GXY_PRE_KEYS', set())",
                "for key, value in list(globals().items()):",
                "    if key in pre_keys or key.startswith('_'):",
                "        continue",
                "    if callable(value):",
                "        continue",
                "    if isinstance(value, (int, float, str, bool)):",
                '        summary_lines.append(f"{key} = {value!r}")',
                "    elif isinstance(value, (list, tuple)) and len(value) <= 10:",
                '        summary_lines.append(f"{key} = {value!r}")',
                "    elif isinstance(value, dict) and len(value) <= 10:",
                "        try:",
                "            preview = {k: value[k] for k in list(value)[:5]}",
                '            summary_lines.append(f"{key} = {preview!r}")',
                "        except Exception:",
                "            pass",
                "try:",
                "    del globals()['_GXY_PRE_KEYS']",
                "except KeyError:",
                "    pass",
                "result = '\\n'.join(summary_lines)",
                "result",
            ].join("\n"),
        );

        const postArtifactsJson = await py.runPythonAsync(
            "import json, os\n" +
                "try:\n" +
                "    files = os.listdir('generated_file')\n" +
                "except Exception:\n" +
                "    files = []\n" +
                "json.dumps(sorted(files))\n",
        );
        const postArtifacts: string[] = JSON.parse(postArtifactsJson);
        const newArtifacts = postArtifacts.filter((name) => !preArtifacts.has(name));

        const summaryParts: string[] = [];
        if (scalarSummary && scalarSummary.trim()) {
            summaryParts.push(scalarSummary.trim());
        }
        if (newArtifacts.length) {
            summaryParts.push(`generated_files = ${JSON.stringify(newArtifacts)}`);
        }
        if (summaryParts.length === 0) {
            summaryParts.push("execution_succeeded");
        }
        if (summaryParts.length) {
            const summaryText = summaryParts.join("\n");
            if (stdoutBuffer && !stdoutBuffer.endsWith("\n")) {
                stdoutBuffer += "\n";
            }
            stdoutBuffer += summaryText;
        }

        return { success: true };
    } catch (error: unknown) {
        const message = error instanceof Error ? error.message : String(error);
        if (!stderrBuffer.includes(message)) {
            stderrBuffer += `\n${message}`;
        }
        return { success: false, error: message };
    } finally {
        try {
            await py.runPythonAsync(
                [
                    "import builtins as _gxy_builtins",
                    "original_open = globals().get('_GXY_ORIGINAL_OPEN')",
                    "if original_open is not None:",
                    "    _gxy_builtins.open = original_open",
                    "load_dataset = globals().get('_GXY_ORIGINAL_LOAD_DATASET', load_dataset)",
                    "get_dataset_path = globals().get('_GXY_ORIGINAL_GET_DATASET_PATH', get_dataset_path)",
                ].join("\n"),
            );
        } catch (restoreError) {
            // ignore restoration issues
        }
    }
}
async function collectArtifacts(py: any): Promise<{ artifacts: PyodideArtifact[]; transferables: ArrayBuffer[] }> {
    const artifacts: PyodideArtifact[] = [];
    const transferables: ArrayBuffer[] = [];

    const visitDirectory = (directory: string, relativePrefix = "") => {
        let entries: string[] = [];
        try {
            entries = py.FS.readdir(directory);
        } catch (err) {
            return;
        }
        for (const entry of entries) {
            if (entry === "." || entry === "..") {
                continue;
            }
            const filePath = `${directory}/${entry}`;
            const relativeName = relativePrefix ? `${relativePrefix}/${entry}` : entry;
            let stats: any;
            try {
                stats = py.FS.stat(filePath);
            } catch (err) {
                continue;
            }
            if (py.FS.isDir(stats.mode)) {
                visitDirectory(filePath, relativeName);
                continue;
            }
            try {
                const data = py.FS.readFile(filePath);
                const buffer = data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength);
                artifacts.push({
                    name: relativeName,
                    path: filePath,
                    size: stats.size,
                    mime_type: guessMimeType(relativeName),
                    binary: buffer,
                });
                transferables.push(buffer);
            } catch (err) {
                // Skip unreadable artifacts
            }
        }
    };

    visitDirectory(OUTPUT_ROOT);

    return { artifacts, transferables };
}

function cleanupDatasets(py: any, datasets: Array<{ path: string }>) {
    for (const dataset of datasets) {
        try {
            py.FS.unlink(dataset.path);
        } catch (err) {
            // ignore
        }
    }
}

function clearDirectory(py: any, path: string) {
    let entries: string[];
    try {
        entries = py.FS.readdir(path);
    } catch (err) {
        return;
    }
    for (const entry of entries) {
        if (entry === "." || entry === "..") {
            continue;
        }
        const target = `${path}/${entry}`;
        try {
            const stats = py.FS.stat(target);
            if (py.FS.isDir(stats.mode)) {
                clearDirectory(py, target);
                py.FS.rmdir(target);
            } else {
                py.FS.unlink(target);
            }
        } catch (err) {
            // ignore
        }
    }
}

function sanitizeFilename(value: string): string {
    return value.replace(/[^A-Za-z0-9_.-]/g, "_");
}

function uniqueAliases(values: Array<string | undefined | null>): string[] {
    const seen = new Set<string>();
    for (const value of values) {
        const alias = (value || "").trim();
        if (alias && !seen.has(alias)) {
            seen.add(alias);
        }
    }
    return Array.from(seen);
}

function guessMimeType(name?: string): string {
    if (!name) {
        return "application/octet-stream";
    }
    const lower = name.toLowerCase();
    if (lower.endsWith(".png")) {
        return "image/png";
    }
    if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) {
        return "image/jpeg";
    }
    if (lower.endsWith(".svg")) {
        return "image/svg+xml";
    }
    if (lower.endsWith(".json")) {
        return "application/json";
    }
    if (lower.endsWith(".csv")) {
        return "text/csv";
    }
    if (lower.endsWith(".tsv")) {
        return "text/tab-separated-values";
    }
    if (lower.endsWith(".txt")) {
        return "text/plain";
    }
    return "application/octet-stream";
}

function buildAliasMap(datasets: Array<{ id: string; aliases: string[] }>): PyodideAliasMap {
    const map: PyodideAliasMap = {};
    for (const dataset of datasets) {
        const datasetId = dataset.id;
        if (datasetId) {
            map[datasetId] = datasetId;
        }
        for (const alias of dataset.aliases) {
            if (alias) {
                map[alias] = datasetId;
            }
        }
    }
    return map;
}
