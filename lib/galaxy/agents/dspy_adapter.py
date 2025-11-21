"""DSPy planner integration for the Galaxy Data Analysis agent."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, ClassVar

DSPY_IMPORT_ERROR: Optional[Exception] = None

try:  # Optional dependency
    import dspy
    try:
        from dspy.teleprompt import BootstrapFewShot
    except ImportError:  # pragma: no cover - optional component
        BootstrapFewShot = None  # type: ignore[assignment]

    HAS_DSPY = True
except ImportError as exc:  # pragma: no cover - DSPy is optional
    HAS_DSPY = False
    dspy = None  # type: ignore[assignment]
    BootstrapFewShot = None  # type: ignore[assignment]
    DSPY_IMPORT_ERROR = exc

log = logging.getLogger(__name__)

if not HAS_DSPY:
    log.warning("DSPy import failed: %s", DSPY_IMPORT_ERROR)


if HAS_DSPY:

    GENERATED_FILES_SUBDIR = "generated_files"

    class DataAnalysisSignature(dspy.Signature):
        """Minimal DSPy signature used for Galaxy's data analysis agent."""

        context = dspy.InputField(
            desc="Conversation context, dataset metadata, and execution history."
        )
        question = dspy.InputField(desc="The user's data analysis request.")
        answer = dspy.OutputField(
            desc="JSON string with 'explanation', 'plots', 'files', 'next_steps_suggestion'."
        )

    def load_examples_from_json(json_file_path: Path) -> List[dspy.Example]:
        examples: List[dspy.Example] = []
        if not json_file_path.exists():
            log.debug("Examples JSON file not found: %s", json_file_path)
            return examples

        try:
            with json_file_path.open('r', encoding='utf-8') as handle:
                data = json.load(handle)
        except Exception as exc:
            log.warning("Failed to load examples from %s: %s", json_file_path, exc)
            return examples

        for item in data:
            answer_payload = item.get('answer') or item.get('final_answer') or item.get('finalAnswer')
            example = dspy.Example(
                question=item.get('question'),
                context=item.get('context'),
                rationale=item.get('rationale'),
                answer=answer_payload,
            ).with_inputs('question', 'context')
            examples.append(example)
        return examples

    def validation_metric(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> bool:
        try:
            payload = json.loads(prediction.answer) if hasattr(prediction, 'answer') else {}
        except Exception:
            return False

        explanation = payload.get('explanation')
        plots = payload.get('plots')
        files = payload.get('files')
        return bool(explanation) and isinstance(plots, list) and isinstance(files, list)

    CODE_REACT_CLS = getattr(dspy, "CodeReact", None)
    REACT_CLASS = CODE_REACT_CLS or dspy.ReAct

    class CodeCaptureTool(dspy.Tool):
        """Captures Python code emitted by the DSPy CodeReact planner."""

        def __init__(self, max_calls: int = 1):
            super().__init__(
                func=self._tool_impl,
                name="python_code_executor",
                desc="Capture generated Python code to execute within Galaxy's sandbox.",
            )
            object.__setattr__(self, "_captured", [])
            object.__setattr__(self, "_max_calls", max_calls)

        def _tool_impl(self, code: str) -> str:  # pragma: no cover - pure DSPy execution
            code = (code or "").strip()
            if not code:
                return "No code supplied to execute."

            if len(self._captured) >= self._max_calls:
                return "Code captured previously. Await execution results before issuing more code."

            self._captured.append(code)
            return "Code captured for execution in the Galaxy sandbox."

        def __call__(self, code: str) -> str:
            return self._tool_impl(code)

        @property
        def last_code(self) -> str:
            return self._captured[-1] if self._captured else ""


    class DatasetLookupTool(dspy.Tool):
        """LLM-accessible tool for resolving Galaxy dataset references."""

        def __init__(self, deps):
            from .dataset_resolver import resolve_dataset_reference  # Local import to avoid circular deps

            super().__init__(
                func=self._tool_impl,
                name="dataset_lookup",
                desc="Retrieve Galaxy dataset identifiers matching a user reference.",
            )
            object.__setattr__(self, "_deps", deps)
            object.__setattr__(self, "_resolve", resolve_dataset_reference)

        def _tool_impl(self, reference: str) -> str:  # pragma: no cover - DSPy execution path
            trans = getattr(self._deps, "trans", None)
            user = getattr(self._deps, "user", None)
            if not (trans and user):
                return json.dumps([])

            try:
                matches = self._resolve(trans, user, reference or "")
            except Exception as exc:  # pragma: no cover - database edge cases
                log.warning("Dataset lookup tool failed: %s", exc)
                matches = []
            return json.dumps(matches)

        def __call__(self, reference: str) -> str:
            return self._tool_impl(reference)


    class GalaxyDataAnalysisModule(dspy.Module):  # pragma: no cover - immediate wrapper
        def __init__(self, tools: List[dspy.Tool], max_iters: int = 5):
            super().__init__()
            if CODE_REACT_CLS is None:
                log.warning(
                    "DSPy CodeReact not available; falling back to ReAct module for data analysis agent."
                )
            self.react_agent = REACT_CLASS(
                DataAnalysisSignature,
                tools=tools,
                max_iters=max_iters,
            )
            self._install_tool_guard()

        def _install_tool_guard(self) -> None:
            try:
                tools_dict = self.react_agent.tools
            except AttributeError:
                return

            if not isinstance(tools_dict, dict):
                return

            logger = log
            self._ensure_finish_alias_support(tools_dict)

            class _SafeToolDict(dict):
                def __init__(self, data):
                    super().__init__(data)

                def __getitem__(self, key):
                    if key not in self:
                        available = ', '.join(sorted(self.keys()))
                        if logger:
                            logger.warning(
                                "ReAct emitted unknown tool '%s'; returning error observation. Available tools: %s",
                                key,
                                available,
                            )
                        from dspy import Tool  # local import to avoid circular issues

                        def _invalid_tool(**kwargs):
                            return json.dumps({
                                'status': 'error',
                                'message': f"Invalid tool '{key}'. Available tools: {available}",
                            })

                        return Tool(
                            func=_invalid_tool,
                            name=f'invalid_{key}',
                            desc='Fallback handler for unexpected tool names emitted by the planner.',
                        )
                    return super().__getitem__(key)

            if not isinstance(tools_dict, _SafeToolDict):
                self.react_agent.tools = _SafeToolDict(tools_dict)

        def _ensure_finish_alias_support(self, tools_dict: Dict[str, dspy.Tool]) -> None:
            finish_tool = None
            for name, tool in tools_dict.items():
                if isinstance(name, str) and name.lower() == "finish":
                    finish_tool = tool
                    break
            if not finish_tool or getattr(finish_tool, "_gxy_finish_wrapped", False):
                return

            finish_tool.has_kwargs = True
            alias_fields = ("explanation", "response", "summary", "result", "final_answer")
            original_func = finish_tool.func

            def _finish_proxy(**kwargs):
                if "answer" not in kwargs:
                    for alias in alias_fields:
                        if alias in kwargs:
                            new_kwargs = dict(kwargs)
                            new_kwargs["answer"] = new_kwargs.pop(alias)
                            kwargs = new_kwargs
                            break
                return original_func(**kwargs)

            finish_tool.func = _finish_proxy
            setattr(finish_tool, "_gxy_finish_wrapped", True)

        def forward(self, question, context):
            return self.react_agent(question=question, context=context)


@dataclass
class DSPyPlanResult:
    summary: str
    python_code: str
    requirements: List[str]
    follow_up: List[str]
    plots: List[str]
    files: List[str]
    analysis_steps: List[Dict[str, Any]]
    is_complete: bool
    raw_answer: Dict[str, Any]
    trajectory: Dict[str, Any] = field(default_factory=dict)


class GalaxyDSPyPlanner:
    """Wrapper that executes the DSPy data analysis plan for Galaxy."""

    _GLOBAL_LM_CONFIGURED: bool = False
    _PACKAGE_HINTS: ClassVar[List[tuple[str, str]]] = [
        ("matplotlib", r"\bmatplotlib\b|\bplt\."),
        ("seaborn", r"\bseaborn\b|\bsns\."),
        ("plotly", r"\bplotly\b"),
    ]

    def __init__(self, deps):
        if not HAS_DSPY:
            detail = f": {DSPY_IMPORT_ERROR}" if DSPY_IMPORT_ERROR else ""
            raise ImportError(f"DSPy is not available{detail}")

        from .base import GalaxyAgentDependencies

        if not isinstance(deps, GalaxyAgentDependencies):
            raise TypeError("GalaxyDSPyPlanner expects GalaxyAgentDependencies")

        self._deps = deps
        self._config = deps.config
        self._examples_path = Path(__file__).parent / "examples.json"
        self._lm_configured = False

    def plan(
        self,
        question: str,
        context_text: str,
    ) -> DSPyPlanResult:
        self._configure_lm()
        code_tool = CodeCaptureTool()
        dataset_tool = DatasetLookupTool(self._deps)
        module = GalaxyDataAnalysisModule([code_tool, dataset_tool])

        # Temporarily disable loading/compiling few-shot examples while we
        # stabilise the Galaxy integration. Re-enable with BootstrapFewShot once
        # the execution loop is validated end-to-end.
        examples: List[Any] = []

        try:
            result = module(question=question, context=context_text)
        except Exception as exc:  # pragma: no cover - DSPy runtime path
            log.exception("DSPy module execution failed")
            raise RuntimeError(f"DSPy module execution failed: {exc}") from exc

        answer_text = getattr(result, "answer", None)
        if not answer_text:
            raise RuntimeError("DSPy module did not return an answer")

        try:
            answer_data = json.loads(answer_text)
        except json.JSONDecodeError as exc:  # pragma: no cover - depends on LLM output
            raise RuntimeError(f"DSPy answer not valid JSON: {exc}") from exc

        trajectory: Dict[str, Any] = getattr(result, "trajectory", {}) or {}
        finish_called = any(value == "finish" for key, value in trajectory.items() if key.startswith("tool_name_"))

        # Always retain the last captured code snippet. Even when the DSPy
        # trajectory issues a `finish` tool call, the code still needs to be
        # executed within Galaxy so we can return real observations to the LLM.
        code = code_tool.last_code
        requirements = self._infer_requirements(code)
        summary = (answer_data.get("explanation") or "").strip()
        follow_up = list(answer_data.get("next_steps_suggestion") or [])
        plots = list(answer_data.get("plots") or [])
        files = list(answer_data.get("files") or [])

        analysis_steps = self._build_analysis_steps(
            trajectory,
            summary,
            code,
            requirements,
            finish_called,
            code_tool_name=getattr(code_tool, "name", "python_code_executor"),
        )

        return DSPyPlanResult(
            summary=summary,
            python_code=code,
            requirements=requirements,
            follow_up=follow_up,
            plots=plots,
            files=files,
            analysis_steps=analysis_steps,
            is_complete=finish_called,
            raw_answer=answer_data,
            trajectory=trajectory,
        )

    def _build_analysis_steps(
        self,
        trajectory: Dict[str, Any],
        summary: str,
        code: str,
        requirements: List[str],
        finish_called: bool,
        *,
        code_tool_name: str,
    ) -> List[Dict[str, Any]]:
        steps: List[Dict[str, Any]] = []

        def _iter_indices() -> Iterable[int]:
            for key in trajectory:
                if not key.startswith("thought_"):
                    continue
                suffix = key.split("_", 1)[1]
                if suffix.isdigit():
                    yield int(suffix)

        try:
            for idx in sorted(set(_iter_indices())):
                raw_thought = trajectory.get(f"thought_{idx}")
                thought = str(raw_thought or "").strip()
                if thought:
                    steps.append({"type": "thought", "content": thought})

                tool_name = trajectory.get(f"tool_name_{idx}")
                tool_args = trajectory.get(f"tool_args_{idx}") or {}
                if hasattr(tool_args, "model_dump"):
                    tool_args = tool_args.model_dump()
                elif hasattr(tool_args, "dict"):
                    try:
                        tool_args = tool_args.dict()
                    except Exception:  # pragma: no cover - best effort coercion
                        pass

                observation_raw = trajectory.get(f"observation_{idx}")
                observation = str(observation_raw or "").strip()

                if tool_name == code_tool_name:
                    action_code = ""
                    if isinstance(tool_args, dict):
                        action_code = tool_args.get("code") or ""
                    if not action_code and code:
                        action_code = code
                    action_code = action_code.strip()
                    if action_code:
                        steps.append(
                            {
                                "type": "action",
                                "content": action_code,
                                "requirements": requirements,
                                "status": "pending",
                            }
                        )
                    if observation:
                        steps.append({"type": "observation", "content": observation})

                elif tool_name == "finish":
                    conclusion = summary or observation or "Analysis complete."
                    steps.append({"type": "conclusion", "content": conclusion.strip()})

                elif tool_name:
                    if isinstance(tool_args, dict):
                        action_repr = json.dumps(tool_args)
                    else:
                        action_repr = str(tool_args)
                    steps.append({"type": "action", "content": f"{tool_name} {action_repr}"})
                    if observation:
                        steps.append({"type": "observation", "content": observation})

            if finish_called and not any(step["type"] == "conclusion" for step in steps):
                if summary:
                    steps.append({"type": "conclusion", "content": summary})
        except Exception as exc:  # pragma: no cover - defensive path
            log.debug("Failed to build analysis steps: %s", exc)
            steps = []
            summary_clean = (summary or "").strip()
            if summary_clean:
                steps.append({"type": "thought", "content": summary_clean})
            code_clean = (code or "").strip()
            if code_clean:
                steps.append({"type": "action", "content": code_clean, "requirements": requirements})

        return steps

    def augment_with_execution(
        self,
        question: str,
        context_text: str,
        plan: DSPyPlanResult,
        execution_result: Dict[str, Any],
    ) -> DSPyPlanResult:
        """Re-run the planner with execution feedback appended to the trajectory."""

        self._configure_lm()
        code_tool = CodeCaptureTool()
        dataset_tool = DatasetLookupTool(self._deps)
        module = GalaxyDataAnalysisModule([code_tool, dataset_tool])

        augmented = dict(plan.trajectory) if plan.trajectory else {}
        indices = [
            int(key.split('_')[1])
            for key in augmented
            if '_' in key and key.split('_')[1].isdigit() and key.startswith('thought_')
        ]
        next_index = (max(indices) + 1) if indices else 0

        observation_payload = {
            'success': execution_result.get('success'),
            'stdout': execution_result.get('stdout'),
            'stderr': execution_result.get('stderr'),
            'artifacts': [artifact.get('name') for artifact in execution_result.get('artifacts', [])],
        }
        thought_message = 'Execution results captured; incorporate them before finalising the answer.'
        augmented[f'thought_{next_index}'] = thought_message
        augmented[f'tool_name_{next_index}'] = 'python_code_executor'
        augmented[f'tool_args_{next_index}'] = {'code': plan.python_code or ''}
        augmented[f'observation_{next_index}'] = json.dumps(observation_payload)

        try:
            result = module(question=question, context=context_text, trajectory=augmented)
        except Exception as exc:  # pragma: no cover - DSPy runtime path
            log.exception('DSPy module execution failed during refinement')
            raise RuntimeError(f"DSPy refinement failed: {exc}") from exc

        answer_text = getattr(result, 'answer', None) or ''
        try:
            answer_data = json.loads(answer_text) if answer_text else {}
        except json.JSONDecodeError:
            answer_data = {'explanation': answer_text}

        trajectory = getattr(result, 'trajectory', {}) or {}
        finish_called = any(value == 'finish' for key, value in trajectory.items() if key.startswith('tool_name_'))

        summary = (answer_data.get('explanation') or plan.summary or '').strip()
        follow_up = list(answer_data.get('next_steps_suggestion') or []) or plan.follow_up
        plots = list(answer_data.get('plots') or []) or plan.plots
        files = list(answer_data.get('files') or []) or plan.files
        requirements = plan.requirements
        analysis_steps = self._build_analysis_steps(
            trajectory,
            summary,
            plan.python_code,
            requirements,
            finish_called,
            code_tool_name=getattr(code_tool, 'name', 'python_code_executor'),
        )

        return DSPyPlanResult(
            summary=summary or plan.summary,
            python_code=plan.python_code,
            requirements=requirements,
            follow_up=follow_up,
            plots=plots,
            files=files,
            analysis_steps=analysis_steps or plan.analysis_steps,
            is_complete=finish_called or plan.is_complete,
            raw_answer=answer_data or plan.raw_answer,
            trajectory=trajectory or augmented,
        )

    def _infer_requirements(self, code: str) -> List[str]:
        requirements: List[str] = []
        if not code:
            return requirements
        marker = '# requirements:'
        for line in code.splitlines():
            normalized = line.strip()
            if normalized.lower().startswith(marker):
                _, _, payload = normalized.partition(':')
                for item in payload.split(','):
                    cleaned = item.strip()
                    if cleaned and cleaned not in requirements:
                        requirements.append(cleaned)
                break
        inferred = set(requirements)
        for package, pattern in self._PACKAGE_HINTS:
            try:
                if re.search(pattern, code, flags=re.IGNORECASE):
                    inferred.add(package)
            except re.error:
                continue
        return sorted(inferred)

    def _configure_lm(self) -> None:
        if self._lm_configured or GalaxyDSPyPlanner._GLOBAL_LM_CONFIGURED:
            self._lm_configured = True
            return

        model_name = getattr(self._config, "ai_model", None) or "gpt-4o"
        api_key = getattr(self._config, "ai_api_key", None)
        api_base = getattr(self._config, "ai_api_base_url", None)

        kwargs: Dict[str, Any] = {"model": model_name}
        if api_key:
            kwargs["api_key"] = api_key
        if api_base:
            kwargs["api_base"] = api_base

        lm = dspy.LM(**kwargs)
        dspy.settings.configure(lm=lm, trace=None)
        self._lm_configured = True
        GalaxyDSPyPlanner._GLOBAL_LM_CONFIGURED = True

    def ensure_lm_configured(self) -> None:
        """Ensure the shared DSPy settings are initialized on the current thread."""
        self._configure_lm()

    @lru_cache(maxsize=1)
    def _load_examples(self) -> List[Any]:
        try:
            return load_examples_from_json(self._examples_path)
        except Exception as exc:  # pragma: no cover - file parse path
            log.debug("Unable to load DSPy examples: %s", exc)
            return []
def build_context_text(
    question: str,
    datasets: Iterable[str],
    conversation_history: Iterable[Dict[str, Any]],
    execution_messages: Iterable[Dict[str, Any]],
    examples_snippet: str,
) -> str:
    dataset_lines = (
        "\n".join(
            f"- Dataset {index + 1} (ID: {dataset_id}) — use load_dataset(\"{dataset_id}\") or get_dataset_path(\"{dataset_id}\") (dataset_{index + 1} and other aliases are also available)"
            for index, dataset_id in enumerate(datasets)
        )
        or "- None"
    )

    history_lines = []
    for entry in conversation_history:
        role = entry.get("role", "user")
        content = entry.get("content", "")
        history_lines.append(f"{role}: {content}")
    history_block = "\n".join(history_lines[-8:]) if history_lines else "None"

    execution_lines = []
    for entry in execution_messages:
        stdout = entry.get("stdout", "")
        stderr = entry.get("stderr", "")
        success = entry.get("success", False)
        execution_lines.append(
            f"Execution ({'success' if success else 'error'}):\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        )
    execution_block = "\n\n".join(execution_lines[-4:]) if execution_lines else "None"

    sections = [
        "DATASETS:",
        dataset_lines,
        "",
        "HELPERS:",
        "Use load_dataset('<alias>') to read a pandas DataFrame for a mounted dataset or get_dataset_path('<alias>') to obtain its file path. Aliases include dataset IDs, names, and dataset_<index>.",
        "",
        "QUESTION:",
        question,
        "",
        "CONVERSATION HISTORY:",
        history_block,
        "",
        "RECENT EXECUTIONS:",
        execution_block,
    ]

    if examples_snippet:
        sections.extend(["", "EXAMPLES:", examples_snippet])

    return "\n".join(sections)
