"""Galaxy Data Analysis Agent.

This agent orchestrates the Galaxy data-analysis workflow using DSPy's CodeReact
planner when available and falls back to the standard ReAct module otherwise.
Code generation and execution control are delegated entirely to DSPy.
"""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

from itsdangerous import URLSafeTimedSerializer

from galaxy import exceptions
from galaxy.managers.hdas import HDAManager
from .base import (
    ActionSuggestion,
    ActionType,
    AgentResponse,
    BaseGalaxyAgent,
    GalaxyAgentDependencies,
)
from galaxy.model import HistoryDatasetAssociation

from .dspy_adapter import (
    DSPyPlanResult,
    GalaxyDSPyPlanner,
    build_context_text,
)

log = logging.getLogger(__name__)

class DataAnalysisAgent(BaseGalaxyAgent):
    """Agent orchestrating dataset analysis with generated code execution."""

    USE_PYDANTIC_AGENT = False
    DEBUG_LOG_PATH = Path(tempfile.gettempdir()) / "galaxy_data_analysis_debug.log"
    DEFAULT_TIMEOUT_MS = 20_000
    DATASET_TOKEN_SALT = "galaxy.agents.pyodide.dataset"

    def __init__(self, deps: GalaxyAgentDependencies):
        super().__init__(deps)
        self.agent_type = "data_analysis"
        self._examples_path = Path(__file__).parent / "examples.json"
        self._example_snippets = self._load_example_snippets(self._examples_path)
        self._planner = GalaxyDSPyPlanner(deps)
        self._last_query: str = ""
        self._last_context_text: str = ""

        config = getattr(deps, "config", None)
        self._dataset_token_signer: Optional[URLSafeTimedSerializer] = None
        self._dataset_token_ttl: int = 600
        if config and getattr(config, "id_secret", None):
            self._dataset_token_signer = URLSafeTimedSerializer(config.id_secret, salt=self.DATASET_TOKEN_SALT)
            ttl_default = getattr(config, "pyodide_dataset_token_ttl", 600)
            try:
                ttl_value = int(ttl_default)
            except (TypeError, ValueError):
                ttl_value = 600
            self._dataset_token_ttl = max(60, ttl_value)

    # BaseGalaxyAgent requires these abstract methods, but the DSPy variant does
    # not use the pydantic runtime.
    def _create_agent(self):  # type: ignore[override]
        raise RuntimeError("DataAnalysisAgent relies on DSPy CodeReact and does not expose a pydantic agent.")

    def get_system_prompt(self) -> str:  # type: ignore[override]
        return (
            "You are Galaxy's data analysis agent. Generate Python that runs inside Galaxy's sandboxed execution environment."
            " Use the helper functions load_dataset('<alias>') to obtain a pandas DataFrame or get_dataset_path('<alias>') for filesystem paths."
            " Dataset aliases include the dataset ID, original name, and dataset_<index> values listed in the context."
            " Save any artifacts to ``outputs_dir/generated_file/`` and immediately print a short summary plus the relative paths for every generated artifact so downstream reasoning can consume real observations."
            " Always return a valid JSON object in your final answer; avoid Python reprs or non-JSON constructs."
        )


    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        context = context or {}
        datasets = context.get("dataset_ids", [])
        conversation_history = context.get("conversation_history", [])

        execution_messages = [entry for entry in conversation_history if entry.get("role") == "execution_result"]
        task_history = self._collect_task_history(conversation_history)
        last_executed_task, latest_execution_message = self._match_execution_event(task_history, execution_messages)

        context_text = build_context_text(
            query,
            datasets,
            conversation_history,
            execution_messages,
            self._example_snippets,
        )

        self._last_query = query
        self._last_context_text = context_text

        # Configure DSPy on the current (main) thread before offloading planning work.
        self._planner.ensure_lm_configured()

        try:
            plan: DSPyPlanResult = await asyncio.to_thread(self._planner.plan, query, context_text)
        except Exception as exc:  # pragma: no cover - defensive path
            log.exception("Data analysis planner failed")
            error_message = f"Planning failed: {exc}" if exc else "Planning failed"
            metadata: Dict[str, Any] = {
                "datasets_used": datasets,
                "planner": "dspy",
                "planning_error": str(exc),
            }
            suggestions = [
                ActionSuggestion(
                    action_type=ActionType.REFINE_QUERY,
                    description="Adjust the request and try again.",
                    parameters={},
                    confidence="low",
                    priority=1,
                )
            ]
            return AgentResponse(
                content=error_message,
                confidence="low",
                agent_type=self.agent_type,
                suggestions=suggestions,
                metadata=metadata,
            )

        return self._response_from_plan(
            plan,
            query,
            context_text,
            datasets,
            last_executed_task,
            latest_execution_message,
        )

    def _response_from_plan(
        self,
        plan: DSPyPlanResult,
        question: str,
        context_text: str,
        datasets: List[str],
        last_executed_task: Optional[Dict[str, Any]],
        latest_execution_message: Optional[Dict[str, Any]],
    ) -> AgentResponse:
        active_plan = plan
        code = (active_plan.python_code or "").strip()
        requirements = active_plan.requirements or []
        normalized_requirements = self._normalize_requirements(requirements)

        dataset_descriptors, alias_map = self._dataset_descriptors(datasets)
        log.debug(
            "dataset_descriptors_pre_execution",
            extra={
                "descriptors": dataset_descriptors,
                "alias_map_sample": {key: alias_map[key] for key in list(alias_map)[:5]},
            },
        )
        if last_executed_task:
            if isinstance(last_executed_task.get("datasets"), list):
                dataset_descriptors = last_executed_task.get("datasets") or dataset_descriptors
            if isinstance(last_executed_task.get("alias_map"), dict):
                alias_map = dict(last_executed_task.get("alias_map") or alias_map)

        execution_result: Optional[Dict[str, Any]] = None
        pyodide_task: Optional[Dict[str, Any]] = None

        should_execute = self._should_enqueue_execution(code, normalized_requirements, last_executed_task)
        if should_execute and code:
            pyodide_task = self._build_pyodide_task(code, normalized_requirements, dataset_descriptors, alias_map)
            log.info(
                "Dispatching Pyodide task %s with packages=%s datasets=%s",
                pyodide_task.get("task_id"),
                pyodide_task.get("packages"),
                [descriptor.get("id") for descriptor in dataset_descriptors if descriptor.get("id")],
            )
        elif latest_execution_message and last_executed_task:
            execution_result = self._format_execution_result(
                latest_execution_message,
                alias_map,
                dataset_descriptors,
                last_executed_task,
                normalized_requirements,
            )
            try:
                refined_plan = self._planner.augment_with_execution(question, context_text, active_plan, execution_result)
                active_plan = refined_plan
            except Exception as exc:  # pragma: no cover - defensive path
                log.debug('Planner refinement failed: %s', exc)
            requirements = active_plan.requirements or requirements
            normalized_requirements = self._normalize_requirements(requirements)

        artifact_records: List[Dict[str, Any]] = []
        if execution_result:
            artifact_records = execution_result.get("artifacts") or []
        elif latest_execution_message and not pyodide_task:
            artifact_records = latest_execution_message.get("artifacts") or []
        artifact_plots: List[str] = []
        artifact_files: List[str] = []
        if artifact_records:
            artifact_plots, artifact_files = self._categorize_artifacts(artifact_records)
        if pyodide_task:
            artifact_records = []
            artifact_plots = []
            artifact_files = []

        if active_plan.analysis_steps:
            analysis_steps = [dict(step) for step in active_plan.analysis_steps]
        else:
            base_code = ""
            if execution_result or pyodide_task:
                base_code = code or (last_executed_task.get("code") if last_executed_task else "") or ""
            analysis_steps = self._build_analysis_steps(active_plan.summary, base_code, normalized_requirements)

        if pyodide_task:
            for step in reversed(analysis_steps):
                if step.get("type") == "action":
                    step["status"] = "pending"
                    break

        if execution_result:
            analysis_steps = self._merge_execution_steps(analysis_steps, code, normalized_requirements, execution_result)
            analysis_steps = self._deduplicate_actions(analysis_steps)
        else:
            analysis_steps = self._deduplicate_actions(analysis_steps)

        log.debug(
            "analysis_steps_pre_response",
            extra={
                "steps": analysis_steps,
                "pyodide_task": bool(pyodide_task),
                "execution_result": execution_result.get("success") if execution_result else None,
            },
        )

        summary_text = active_plan.summary or ""

        dataset_ids_used = [str(entry.get("id")) for entry in dataset_descriptors if entry.get("id")] or list(datasets)
        metadata: Dict[str, Any] = {
            "datasets_used": dataset_ids_used,
            "summary": summary_text,
            "analysis_steps": analysis_steps,
            "plots": artifact_plots,
            "files": artifact_files,
            "expected_plots": active_plan.plots,
            "expected_files": active_plan.files,
            "artifacts": artifact_records,
            "examples_used": bool(self._example_snippets),
            "planner": "dspy",
            "completion_state": self._determine_completion_state(active_plan, execution_result),
            "raw_answer": active_plan.raw_answer,
            "requirements": normalized_requirements,
            "dataset_descriptors": dataset_descriptors,
        }

        if pyodide_task:
            metadata["pyodide_task"] = pyodide_task
            metadata["pyodide_status"] = "pending"
            metadata["pyodide_started_at"] = datetime.now(timezone.utc).isoformat()
            metadata["pyodide_context"] = {
                "alias_map": alias_map,
                "datasets": dataset_descriptors,
                "requirements": normalized_requirements,
            }
            metadata["is_complete"] = False
        elif execution_result is not None:
            metadata["execution"] = execution_result
            normalized_code = self._normalize_code(code) if code else ""
            metadata_code = normalized_code or (last_executed_task.get("code") if last_executed_task else "") or ""
            metadata_requirements = (
                normalized_requirements
                if normalized_code
                else (last_executed_task.get("requirements", []) if last_executed_task else normalized_requirements)
            )
            metadata["executed_task"] = {
                "task_id": last_executed_task.get("task_id") if last_executed_task else None,
                "code": metadata_code,
                "requirements": metadata_requirements,
                "datasets": dataset_descriptors,
                "alias_map": alias_map,
            }
            metadata["stdout"] = execution_result.get("stdout", "")
            metadata["stderr"] = execution_result.get("stderr", "")
            metadata["pyodide_status"] = "completed" if execution_result.get("success") else "error"
            metadata["is_complete"] = execution_result.get("success")
            metadata["pyodide_context"] = {
                "alias_map": alias_map,
                "datasets": dataset_descriptors,
                "requirements": normalized_requirements,
            }
        else:
            metadata["pyodide_status"] = "completed" if active_plan.is_complete else "pending"
            metadata["is_complete"] = active_plan.is_complete

        suggestions: List[ActionSuggestion] = []
        if execution_result and not execution_result.get("success", False):
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.REFINE_QUERY,
                    description="Adjust the request and try a different analysis approach.",
                    parameters={},
                    confidence="medium",
                    priority=1,
                )
            )

        follow_up_items = self._normalize_follow_up_items(active_plan.follow_up)
        base_priority = len(suggestions) + 1
        for index, follow in enumerate(follow_up_items):
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.REFINE_QUERY,
                    description=follow,
                    parameters={},
                    confidence="medium",
                    priority=base_priority + index,
                )
            )

        if execution_result and execution_result.get("success"):
            content = self._build_content_from_execution(summary_text, execution_result)
            confidence = "high"
        elif execution_result:
            content = self._build_content_from_execution(summary_text, execution_result)
            confidence = "low"
        elif pyodide_task:
            summary_text = summary_text.strip()
            content = (
                f"{summary_text}\n\nExecuting generated Python in the browser..."
                if summary_text
                else "Executing generated Python in the browser..."
            )
            confidence = "medium"
        else:
            content = active_plan.summary or next(
                (step["content"] for step in analysis_steps if step.get("type") == "thought"),
                "Generated analysis plan.",
            )
            confidence = "high" if active_plan.is_complete else "medium"

        self._record_debug_steps(active_plan, analysis_steps, execution_result)

        return AgentResponse(
            content=content,
            confidence=confidence,
            agent_type=self.agent_type,
            suggestions=suggestions,
            metadata=metadata,
        )

    def _determine_completion_state(self, plan: DSPyPlanResult, execution_result: Optional[Dict[str, Any]]) -> str:
        if execution_result is not None:
            return "complete" if execution_result.get("success") else "error"
        return "complete" if plan.is_complete else "pending"

    def _collect_task_history(self, conversation_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        tasks: List[Dict[str, Any]] = []
        for entry in conversation_history:
            agent_response = entry.get("agent_response")
            if not isinstance(agent_response, dict):
                continue
            metadata = agent_response.get("metadata") or {}
            context_payload = metadata.get("pyodide_context") or {}
            for key in ("executed_task", "pyodide_task"):
                candidate = metadata.get(key)
                if not isinstance(candidate, dict):
                    continue
                code = candidate.get("code")
                packages = candidate.get("requirements") or candidate.get("packages") or []
                if not packages and isinstance(context_payload.get("requirements"), list):
                    packages = context_payload.get("requirements")
                if not code:
                    continue
                normalized = {
                    "task_id": candidate.get("task_id"),
                    "code": self._normalize_code(str(code)),
                    "requirements": self._normalize_requirements(packages),
                }
                if isinstance(candidate.get("alias_map"), dict):
                    normalized["alias_map"] = dict(candidate["alias_map"])
                elif isinstance(context_payload.get("alias_map"), dict):
                    normalized["alias_map"] = dict(context_payload["alias_map"])
                if isinstance(candidate.get("datasets"), list):
                    normalized["datasets"] = candidate["datasets"]
                elif isinstance(context_payload.get("datasets"), list):
                    normalized["datasets"] = context_payload["datasets"]
                tasks.append(normalized)
        return tasks

    def _match_execution_event(
        self,
        task_history: List[Dict[str, Any]],
        execution_messages: List[Dict[str, Any]],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        if not task_history and not execution_messages:
            return None, None

        task_lookup: Dict[str, Dict[str, Any]] = {}
        for task in task_history:
            task_id = task.get("task_id")
            if task_id:
                task_lookup[str(task_id)] = task

        matched_task: Optional[Dict[str, Any]] = None
        matched_execution: Optional[Dict[str, Any]] = None

        for entry in reversed(execution_messages):
            task_id = entry.get("task_id")
            if task_id and str(task_id) in task_lookup:
                matched_task = task_lookup[str(task_id)]
                matched_execution = entry
                break

        if matched_task is None and task_history:
            matched_task = task_history[-1]

        return matched_task, matched_execution

    def _dataset_descriptors(
        self,
        dataset_ids: List[str],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        if not dataset_ids:
            return [], {}

        alias_map, metadata = self._prepare_dataset_aliases(dataset_ids)
        descriptors: List[Dict[str, Any]] = []
        alias_index: Dict[str, str] = {}

        for entry in metadata:
            dataset_id = entry.get("id")
            if not dataset_id:
                continue
            aliases = entry.get("aliases") or []
            descriptor = {
                "id": dataset_id,
                "name": entry.get("name"),
                "size": entry.get("size"),
                "aliases": aliases,
                "path": entry.get("path"),
            }
            descriptors.append(descriptor)
            alias_index[str(dataset_id)] = str(dataset_id)
            for alias in aliases:
                alias_index[str(alias)] = str(dataset_id)

        if not descriptors:
            for dataset_id in dataset_ids:
                descriptors.append(
                    {
                        "id": dataset_id,
                        "name": dataset_id,
                        "size": None,
                        "aliases": [dataset_id],
                    }
                )
                alias_index[str(dataset_id)] = str(dataset_id)

        if alias_map:
            alias_index.update({str(key): str(value) for key, value in alias_map.items()})

        return descriptors, alias_index

    def _build_pyodide_task(
        self,
        code: str,
        requirements: List[str],
        dataset_descriptors: List[Dict[str, Any]],
        alias_map: Dict[str, str],
    ) -> Dict[str, Any]:
        task_id = str(uuid.uuid4())
        sanitized_code = self._sanitize_pyodide_code(code)
        packages_set = {pkg for pkg in requirements if pkg}
        packages_set.add("pandas")
        packages = sorted(packages_set)
        files: List[Dict[str, Any]] = []
        for descriptor in dataset_descriptors:
            dataset_id = descriptor.get("id")
            if not dataset_id:
                continue
            download_url = self._dataset_download_url(str(dataset_id))
            if not download_url:
                log.warning("Unable to generate download URL for dataset %s", dataset_id)
                continue
            files.append(
                {
                    "id": dataset_id,
                    "name": descriptor.get("name") or dataset_id,
                    "size": descriptor.get("size"),
                    "aliases": descriptor.get("aliases") or [],
                    "url": download_url,
                    "mime_type": self._guess_mime_type(descriptor.get("name")),
                }
            )

        config: Dict[str, Any] = {}
        config_index = getattr(getattr(self.deps, "config", None), "pyodide_index_url", None)
        if config_index:
            config["index_url"] = config_index

        task: Dict[str, Any] = {
            "task_id": task_id,
            "action": "ExecutePythonInBrowser",
            "code": sanitized_code,
            "packages": packages,
            "files": files,
            "alias_map": alias_map,
            "timeout_ms": self.DEFAULT_TIMEOUT_MS,
        }
        if config:
            task["config"] = config
        return task

    def _format_execution_result(
        self,
        execution_message: Dict[str, Any],
        alias_map: Dict[str, str],
        dataset_descriptors: List[Dict[str, Any]],
        executed_task: Dict[str, Any],
        requirements: List[str],
    ) -> Dict[str, Any]:
        result = {
            "success": bool(execution_message.get("success")),
            "stdout": (execution_message.get("stdout") or "").strip(),
            "stderr": (execution_message.get("stderr") or "").strip(),
            "artifacts": execution_message.get("artifacts") or [],
            "task_id": execution_message.get("task_id"),
            "dataset_aliases": alias_map,
            "datasets": dataset_descriptors,
            "requirements": requirements,
        }
        if executed_task.get("alias_map"):
            result["dataset_aliases"] = dict(executed_task.get("alias_map"))
        if executed_task.get("datasets"):
            result["datasets"] = executed_task.get("datasets")
        return result

    def _sanitize_pyodide_code(self, code: str) -> str:
        if not code:
            return code
        patterns = [
            re.compile(r"^\s*import\s+pyodide\b"),
            re.compile(r"^\s*from\s+pyodide\b"),
            re.compile(r"pyodide\.loadPackage"),
            re.compile(r"micropip\.install"),
        ]
        sanitized_lines: List[str] = []
        for line in code.splitlines():
            if any(pattern.search(line) for pattern in patterns):
                continue
            sanitized_lines.append(line)
        return "\n".join(sanitized_lines).strip()

    def _dataset_download_url(self, dataset_id: str) -> Optional[str]:
        token = self._sign_dataset_download_token(dataset_id)
        if not token:
            return None

        path = f"/api/chat/datasets/{dataset_id}/download"
        trans = getattr(self.deps, "trans", None)
        base_url = path
        url_builder = getattr(trans, "url_builder", None)
        if callable(url_builder):
            try:
                base_url = url_builder(path, qualified=False)  # Prefer relative URL for same-origin fetch
            except TypeError:
                try:
                    base_url = url_builder(path)
                except Exception:
                    base_url = path
            except Exception:
                base_url = path

        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}{urlencode({'token': token})}"

    def _sign_dataset_download_token(self, dataset_id: str) -> Optional[str]:
        if not self._dataset_token_signer:
            return None
        trans = getattr(self.deps, "trans", None)
        if not trans:
            return None

        session = getattr(trans, "galaxy_session", None)
        session_id = getattr(session, "id", None)

        encoded_user_id = None
        if self.deps.user and getattr(trans, "security", None):
            try:
                encoded_user_id = trans.security.encode_id(self.deps.user.id)
            except Exception:
                encoded_user_id = None

        payload = {
            "dataset_id": dataset_id,
            "user_id": encoded_user_id,
            "session_id": session_id,
        }
        return self._dataset_token_signer.dumps(payload)

    def _guess_mime_type(self, name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        mime_type, _ = mimetypes.guess_type(str(name))
        return mime_type

    def _prepare_dataset_aliases(self, dataset_ids: List[str]) -> tuple[Dict[str, str], List[Dict[str, Any]]]:
        trans = getattr(self.deps, "trans", None)
        app = getattr(trans, "app", None)
        if not dataset_ids or not trans or not getattr(trans, "security", None) or not app:
            return {}, []

        # Prefer the app's HDAManager if available; otherwise construct one when dependencies exist.
        hda_manager = getattr(app, "hda_manager", None)
        if hda_manager is None:
            user_manager = getattr(app, "user_manager", None)
            ldda_manager = getattr(app, "ldda_manager", None)
            if user_manager and ldda_manager:
                hda_manager = HDAManager(app, user_manager, ldda_manager)
            else:
                log.warning("HDAManager not available; skipping dataset alias preparation.")
                return {}, []

        alias_map: Dict[str, str] = {}
        log.debug('Preparing dataset aliases', extra={'dataset_ids': dataset_ids})
        metadata: List[Dict[str, Any]] = []
        used_aliases: set[str] = set()

        for index, encoded_id in enumerate(dataset_ids, start=1):
            try:
                decoded_id = trans.security.decode_id(encoded_id)
                hda = hda_manager.get_accessible(decoded_id, trans.user)
                ensure_on_disk = getattr(hda_manager, "ensure_dataset_on_disk", None)
                if callable(ensure_on_disk):
                    ensure_on_disk(trans, hda)
                else:
                    hda_manager.dataset_manager.ensure_dataset_on_disk(trans, hda)
            except exceptions.ItemAccessibilityException:
                log.warning("Dataset %s is not accessible to the current user", encoded_id)
                continue
            except exceptions.Conflict as exc:
                log.warning("Dataset %s is not in a usable state: %s", encoded_id, exc)
                continue
            except Exception as exc:  # pragma: no cover - defensive guard
                log.warning("Error preparing dataset %s: %s", encoded_id, exc)
                continue

            file_path = self._get_dataset_file_path(hda)
            if not file_path or not os.path.exists(file_path):
                log.warning("Dataset file is not available for %s", encoded_id)
                continue

            alias_candidates = [encoded_id, f"dataset_{index}"]
            if hda.name:
                alias_candidates.append(hda.name)
                alias_candidates.append(self._sanitize_alias(hda.name))

            file_basename = Path(file_path).name
            alias_candidates.append(file_basename)
            alias_candidates.append(self._sanitize_alias(file_basename))

            unique_aliases = []
            for candidate in alias_candidates:
                if not candidate:
                    continue
                alias_str = candidate.strip()
                if not alias_str or alias_str in used_aliases:
                    continue
                used_aliases.add(alias_str)
                unique_aliases.append(alias_str)
                alias_map[alias_str] = file_path

            alias_map[file_basename] = file_path
            alias_map[self._sanitize_alias(file_basename)] = file_path
            log.debug('prepared_dataset_entry', extra={'id': encoded_id, 'aliases': unique_aliases, 'path': file_path})
            metadata.append(
                {
                    "id": encoded_id,
                    "name": hda.name or f"dataset_{index}",
                    "path": file_path,
                    "size": os.path.getsize(file_path) if os.path.exists(file_path) else None,
                    "aliases": unique_aliases,
                }
            )

        return alias_map, metadata

    def _get_dataset_file_path(self, hda: HistoryDatasetAssociation) -> Optional[str]:
        dataset = getattr(hda, "dataset", None)
        candidates = [getattr(hda, "file_name", None)]
        if dataset is not None:
            candidates.append(getattr(dataset, "file_name", None))
            if hasattr(dataset, "get_file_name"):
                try:
                    candidates.append(dataset.get_file_name())
                except Exception:  # pragma: no cover - backend-specific
                    pass

        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate

        app = getattr(getattr(self.deps, "trans", None), "app", None)
        if app and getattr(app, "object_store", None) and dataset is not None:
            try:
                filename = app.object_store.get_filename(dataset)
                if filename and os.path.exists(filename):
                    return filename
            except Exception:  # pragma: no cover - backend-specific
                pass

        return candidates[0] if candidates else None

    def _merge_execution_steps(
        self,
        analysis_steps: List[Dict[str, Any]],
        code: str,
        requirements: List[str],
        execution_result: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        steps: List[Dict[str, Any]] = []
        action_added = False
        normalized_code = (code or "").strip()
        seen_codes: set[str] = set()

        for step in analysis_steps:
            step_copy = dict(step)
            if step_copy.get("type") == "action":
                content_normalized = self._normalize_code(step_copy.get("content", ""))
                if content_normalized in seen_codes:
                    continue
                if (
                    not action_added
                    and normalized_code
                    and content_normalized == self._normalize_code(normalized_code)
                ):
                    step_copy["content"] = normalized_code
                    step_copy["requirements"] = requirements
                    step_copy["status"] = "completed" if execution_result.get("success") else "error"
                    steps.append(step_copy)
                    steps.append(self._build_observation_step(execution_result))
                    action_added = True
                    seen_codes.add(content_normalized)
                    continue
                seen_codes.add(content_normalized)
            steps.append(step_copy)

        if not action_added and normalized_code:
            steps.append(
                {
                    "type": "action",
                    "content": normalized_code,
                    "requirements": requirements,
                    "status": "completed" if execution_result.get("success") else "error",
                }
            )
            steps.append(self._build_observation_step(execution_result))

        return steps

    def _build_observation_step(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        stdout_value = execution_result.get("stdout", "")
        stderr_value = execution_result.get("stderr", "")
        success = execution_result.get("success", False)
        parts: List[str] = []
        if stdout_value:
            parts.append(f"stdout:\n{self._truncate_output(stdout_value)}")
        if stderr_value:
            parts.append(f"stderr:\n{self._truncate_output(stderr_value)}")
        if not parts:
            parts.append("Execution completed successfully." if success else "Execution failed.")

        return {
            "type": "observation",
            "content": "\n\n".join(parts),
            "stdout": stdout_value,
            "stderr": stderr_value,
            "success": success,
            "status": "completed" if success else "error",
        }

    def _build_content_from_execution(
        self, summary: Optional[str], execution_result: Dict[str, Any]
    ) -> str:
        segments: List[str] = []
        summary_text = (summary or "").strip()
        if summary_text:
            segments.append(summary_text)

        stdout_value = execution_result.get("stdout", "").strip()
        stderr_value = execution_result.get("stderr", "").strip()
        error_message = execution_result.get("error", "")

        if not execution_result.get("success", False):
            if stderr_value:
                segments.append(f"Execution error:\n{self._truncate_output(stderr_value)}")
            elif error_message:
                segments.append(f"Execution error:\n{self._truncate_output(str(error_message))}")

        if not segments:
            segments.append("Generated analysis code executed successfully." if execution_result.get("success") else "Generated analysis code failed.")

        return "\n\n".join(segments).strip()

    def _sanitize_alias(self, value: str) -> str:
        if not value:
            return ""
        sanitized = re.sub(r"[^0-9A-Za-z_]+", "_", value.strip())
        sanitized = re.sub(r"_{2,}", "_", sanitized).strip('_')
        if sanitized and not sanitized[0].isalpha():
            sanitized = f"dataset_{sanitized}"
        return sanitized

    def _deduplicate_actions(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped: List[Dict[str, Any]] = []
        seen_codes: set[str] = set()
        skip_next_observation = False
        for step in steps:
            step_type = str(step.get("type", "") or "").lower()
            if step_type == "action":
                normalized = self._normalize_code(step.get("content", ""))
                if normalized in seen_codes:
                    skip_next_observation = True
                    continue
                seen_codes.add(normalized)
                skip_next_observation = False
                deduped.append(step)
            elif step_type == "observation":
                if skip_next_observation:
                    skip_next_observation = False
                    continue
                if (
                    deduped
                    and str(deduped[-1].get("type", "") or "").lower() == "observation"
                    and self._normalize_code(deduped[-1].get("content", "")) == self._normalize_code(step.get("content", ""))
                ):
                    continue
                deduped.append(step)
            else:
                deduped.append(step)
        return deduped

    def _truncate_output(self, value: str, limit: int = 1200) -> str:
        text = (value or "").strip()
        if len(text) <= limit:
            return text
        return text[:limit].rstrip() + "\n..."

    def _categorize_artifacts(self, artifacts: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
        plot_paths: List[str] = []
        file_paths: List[str] = []
        seen: set[str] = set()
        for artifact in artifacts or []:
            name = str(artifact.get("name") or artifact.get("path") or "").strip()
            if not name:
                continue
            normalized = name if name.startswith("generated_file") else f"generated_file/{name}"
            if normalized in seen:
                continue
            seen.add(normalized)
            mime = str(artifact.get("mime_type") or "").lower()
            target = plot_paths if mime.startswith("image/") else file_paths
            target.append(normalized)
        return plot_paths, file_paths

    def _should_enqueue_execution(
        self,
        code: str,
        requirements: List[str],
        last_executed_task: Optional[Dict[str, Any]],
    ) -> bool:
        if not code.strip():
            return False
        if not last_executed_task:
            return True
        return not self._tasks_equivalent(code, requirements, last_executed_task)

    def _tasks_equivalent(
        self,
        code: str,
        requirements: List[str],
        last_task: Dict[str, Any],
    ) -> bool:
        normalized_code = self._normalize_code(code)
        last_code = last_task.get("code")
        if normalized_code != last_code:
            return False
        normalized_requirements = self._normalize_requirements(requirements)
        last_requirements = last_task.get("requirements", [])
        return normalized_requirements == last_requirements

    def _normalize_code(self, code: str) -> str:
        return "\n".join(line.rstrip() for line in (code or "").strip().splitlines())

    def _record_debug_steps(
        self,
        plan: DSPyPlanResult,
        analysis_steps: List[Dict[str, Any]],
        execution_result: Optional[Dict[str, Any]],
    ) -> None:
        """Persist the most recent planning steps for temporary debugging."""

        timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        payload = {
            "timestamp": timestamp,
            "query": getattr(self, "_last_query", ""),
            "context_text": getattr(self, "_last_context_text", ""),
            "summary": plan.summary,
            "python_code": plan.python_code,
            "analysis_steps": analysis_steps,
            "execution_result": execution_result,
            "raw_answer": plan.raw_answer,
        }

        try:
            with self.DEBUG_LOG_PATH.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload) + "\n")
        except Exception as exc:  # pragma: no cover - best effort logging
            log.debug("Unable to write debug steps log: %s", exc)

    def _normalize_follow_up_items(self, follow_up: Optional[List[Any]]) -> List[str]:
        if not follow_up:
            return []
        items: List[str] = []
        for entry in follow_up:
            if entry is None:
                continue
            if isinstance(entry, str):
                cleaned = entry.strip()
                if cleaned:
                    items.append(cleaned)
            elif isinstance(entry, (list, tuple)):
                joined = " ".join(str(part).strip() for part in entry if str(part).strip())
                if joined:
                    items.append(joined)
            else:
                text = str(entry).strip()
                if text:
                    items.append(text)
        return items

    def _normalize_requirements(self, requirements: List[Any]) -> List[str]:
        return sorted({str(req).strip() for req in requirements if str(req).strip()})

    def _build_analysis_steps(self, summary: str, code: str, requirements: List[str]) -> List[Dict[str, Any]]:
        steps: List[Dict[str, Any]] = []
        summary_clean = (summary or "").strip()
        code_clean = (code or "").strip()

        if summary_clean:
            steps.append(
                {
                    "type": "thought" if code_clean else "conclusion",
                    "content": summary_clean,
                }
            )

        if code_clean:
            steps.append(
                {
                    "type": "action",
                    "content": code_clean,
                    "requirements": requirements,
                }
            )

        return steps


    @staticmethod
    @lru_cache(maxsize=1)
    def _load_example_snippets(path: Path) -> str:
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
                snippets = []
                for item in data[:2]:
                    question = item.get("question")
                    answer = item.get("answer") or item.get("final_answer") or item.get("finalAnswer")
                    if question and answer:
                        snippets.append(
                            f"\n### Example\nQuestion: {question}\nAnswer: {answer}"
                        )
                return "".join(snippets)
        except FileNotFoundError:
            log.debug("Examples file not found at %s", path)
        except Exception as exc:
            log.debug("Failed to load example snippets: %s", exc)
        return ""
