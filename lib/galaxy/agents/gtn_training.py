"""GTN Training Agent - searches Galaxy Training Network tutorials and FAQs."""

import json
import logging
import re
from pathlib import Path
from typing import (
    Any,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
)
from pydantic_ai import (
    Agent,
    RunContext,
)

from galaxy.schema.agents import ConfidenceLevel
from .base import (
    ActionSuggestion,
    ActionType,
    AgentResponse,
    AgentType,
    BaseGalaxyAgent,
    extract_result_content,
    extract_structured_output,
    extract_usage_info,
    GalaxyAgentDependencies,
    normalize_llm_text,
)
from .gtn import GTNSearchDB
from langchain_openai import OpenAIEmbeddings

log = logging.getLogger(__name__)

GTN_TRAINING_BASE_URL = "https://training.galaxyproject.org/training-material"


class GTNSearchResponse(BaseModel):
    """Structured response from GTN training agent."""

    tutorials: list[dict[str, Any]] = Field(default_factory=list, description="List of matching tutorials")
    workflows: list[dict[str, Any]] = Field(default_factory=list, description="List of matching workflows")
    faqs: list[dict[str, Any]] = Field(default_factory=list, description="List of matching FAQs")
    summary: str = Field(..., description="Natural language summary of findings")
    learning_path: Optional[str] = Field(None, description="Suggested learning progression")
    prerequisites: list[str] = Field(default_factory=list, description="Recommended prerequisites")
    total_time: Optional[str] = Field(None, description="Estimated total time for suggested tutorials")


class GTNTrainingAgent(BaseGalaxyAgent):
    """Searches GTN tutorials to help users find training materials and learning paths."""

    agent_type = AgentType.GTN_TRAINING

    def __init__(self, deps: GalaxyAgentDependencies):
        super().__init__(deps)

        db_path = getattr(deps.config, "gtn_database_path", None)
        download_url = getattr(deps.config, "gtn_database_url", None)

        self.gtn_db: GTNSearchDB | None = None
        try:
            self.gtn_db = GTNSearchDB(db_path=db_path, download_url=download_url)
            log.info("GTN database initialized successfully")
        except (OSError, RuntimeError) as e:
            log.warning(f"GTN database not available: {e}")
            self.gtn_db = None

    def _create_agent(self) -> Agent[GalaxyAgentDependencies, Any]:
        if not self._supports_structured_output():
            return Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
                system_prompt=self._get_simple_system_prompt(),
            )

        agent = Agent(
            self._get_model(),
            deps_type=GalaxyAgentDependencies,
            output_type=GTNSearchResponse,
            system_prompt=self.get_system_prompt(),
        )

        @agent.tool
        async def search_gtn_tutorial_vectors(
            ctx: RunContext[GalaxyAgentDependencies],
            query: str,
            topic: Optional[str] = None,
            difficulty: Optional[str] = None,
            hands_on_only: bool = False,
            limit: int = 2,
        ) -> str:
            """Search GTN tutorials using full-text search over titles, descriptions, and content."""
            if not self.gtn_db:
                return json.dumps({"error": "GTN database not available"})
            try:
                embeddings, persist_dir = self._vector_search_dependencies()
                results = self.gtn_db.search_gtn_vector_db(
                    query=query,
                    embeddings=embeddings,
                    persist_dir=persist_dir,
                    collection_name="gtn_tutorials",
                    limit=limit,
                )
                log.info(f"GTN search found {len(results)} results, vector search found {len(results)} results for query: '{query}'")
                log.info(f"Vector search results: {results}")
                log.info(f"Vector search results (dict): {[r.to_dict() for r in results]}")
                

                return json.dumps(
                    {
                        "results": [r.to_dict() for r in results],
                        "count": len(results)
                    }
                )
            except (AttributeError, KeyError, TypeError) as e:
                log.warning(f"GTN vector search failed: {e}")
                return json.dumps({"error": str(e)})

        @agent.tool
        async def search_gtn_workflow_vectors(
            ctx: RunContext[GalaxyAgentDependencies],
            query: str,
            limit: int = 3,
        ) -> str:
            """Search workflow vectors for end-to-end analysis workflows relevant to the query."""
            if not self.gtn_db:
                return json.dumps({"error": "GTN database not available"})
            try:
                embeddings, persist_dir = self._vector_search_dependencies()
                results = self.gtn_db.search_workflow_vector_db(
                    query=query,
                    embeddings=embeddings,
                    persist_dir=persist_dir,
                    collection_name="iwc_workflows",
                    limit=limit,
                )
                log.info("Workflow vector search found %d results for query: %r", len(results), query)
                log.info(f"Workflow search found {len(results)} results, wf vector search found {len(results)} results for query: '{query}'")
                log.info(f"Workflow Vector search results: {results}")
                log.info(f"Workflow Vector search results (dict): {[r.to_dict() for r in results]}")
                return json.dumps(
                    {
                        "results": [r.to_dict() for r in results],
                        "workflows": [r.to_dict() for r in results],
                        "count": len(results),
                    }
                )
            except (AttributeError, KeyError, TypeError, ValueError) as e:
                log.warning(f"GTN workflow vector search failed: {e}")
                return json.dumps({"error": str(e)})

        @agent.tool
        async def search_gtn_tutorials(
            ctx: RunContext[GalaxyAgentDependencies],
            query: str,
            topic: Optional[str] = None,
            difficulty: Optional[str] = None,
            hands_on_only: bool = False,
            limit: int = 5,
        ) -> str:
            """Search GTN tutorials using full-text search over titles, descriptions, and content."""
            if not self.gtn_db:
                return json.dumps({"error": "GTN database not available"})
            try:
                results = self.gtn_db.search(
                    query=query,
                    topic=topic,
                    difficulty=difficulty,
                    hands_on_only=hands_on_only,
                    limit=limit,
                )
                return json.dumps(
                    {
                        "results": [r.to_dict() for r in results],
                        "count": len(results),
                    }
                )
            except Exception as e:
                log.warning(f"GTN search failed: {e}")
                return json.dumps({"error": str(e)})

        @agent.tool
        async def get_tutorial_content(
            ctx: RunContext[GalaxyAgentDependencies],
            topic: str,
            tutorial: str,
            max_length: int = 1500,
        ) -> str:
            """Get the full content of a specific tutorial by topic and name."""
            if not self.gtn_db:
                return "GTN database not available"
            try:
                content = self.gtn_db.get_tutorial_content(topic, tutorial, max_length)
                return content or f"Tutorial {topic}/{tutorial} not found"
            except Exception as e:
                log.warning(f"Failed to get tutorial content: {e}")
                return f"Error: {e}"

        @agent.tool
        async def list_gtn_topics(ctx: RunContext[GalaxyAgentDependencies]) -> str:
            """List all available GTN tutorial topics."""
            if not self.gtn_db:
                return json.dumps({"error": "GTN database not available"})
            try:
                topics = self.gtn_db.get_topics()
                return json.dumps({"topics": topics, "count": len(topics)})
            except Exception as e:
                log.warning(f"Failed to get topics: {e}")
                return json.dumps({"error": str(e)})

        @agent.tool
        async def search_gtn_faqs(
            ctx: RunContext[GalaxyAgentDependencies],
            query: str,
            category: Optional[str] = None,
            limit: int = 5,
        ) -> str:
            """Search Galaxy / GTN FAQs for short, definitional or how-do-I questions.

            FAQs are curated short answers covering Galaxy interface basics
            ("what is a history", "how do I share a workflow"). Prefer this
            over ``search_gtn_tutorials`` for queries shorter than about
            eight words or phrased as ``what is X`` / ``how do I X``.
            """
            if not self.gtn_db:
                return json.dumps({"error": "GTN database not available"})
            try:
                results = self.gtn_db.search_faqs(query=query, category=category, limit=limit)
                return json.dumps(
                    {
                        "results": [r.to_dict() for r in results],
                        "count": len(results),
                    }
                )
            except Exception as e:
                log.warning(f"GTN FAQ search failed: {e}")
                return json.dumps({"error": str(e)})

        @agent.tool
        async def search_tutorials_by_tools(
            ctx: RunContext[GalaxyAgentDependencies],
            tool_names: list[str],
            limit: int = 5,
        ) -> str:
            """Find tutorials that use specific Galaxy tools."""
            if not self.gtn_db:
                return json.dumps({"error": "GTN database not available"})
            try:
                results = self.gtn_db.search_by_tools(tool_names, limit)
                return json.dumps(
                    {
                        "results": [r.to_dict() for r in results],
                        "count": len(results),
                        "tools_searched": tool_names,
                    }
                )
            except Exception as e:
                log.warning(f"Tool search failed: {e}")
                return json.dumps({"error": str(e)})

        return agent

    def get_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent / "prompts" / "gtn_training.md"
        return prompt_path.read_text()

    @staticmethod
    def _looks_like_workflow_query(query: str) -> bool:
        query_lower = query.lower()
        return any(
            term in query_lower
            for term in (
                "workflow",
                "workflows",
                "pipeline",
                "pipelines",
                "importable",
                "end-to-end",
                "end to end",
            )
        )

    def _vector_search_dependencies(self) -> tuple[OpenAIEmbeddings, Path]:
        persist_dir = Path(getattr(self.deps.config, "vector_database_path", None))
        embedding_base_url = getattr(self.deps.config, "embedding_api_base_url", None)
        embedding_model = getattr(self.deps.config, "embedding_model", None)
        embedding_api_key = getattr(self.deps.config, "embedding_api_key", None) or ""
        embeddings = OpenAIEmbeddings(
            base_url=embedding_base_url,
            model=embedding_model,
            api_key=embedding_api_key,
            tiktoken_enabled=False,  # Disable tiktoken to avoid DNS issues with custom models
            check_embedding_ctx_length=False,  # Disable context length checking
        )
        self.persist_dir = persist_dir
        self.embeddings = embeddings
        return embeddings, persist_dir

    async def process(self, query: str, context: Optional[dict[str, Any]] = None) -> AgentResponse:
        validation_error = self._validate_query(query)
        if validation_error:
            return self._validation_error_response(validation_error)

        if not self.gtn_db:
            return self._build_response(
                content="GTN database is not available. Please ensure it's properly initialized.",
                confidence=ConfidenceLevel.LOW,
                method="error",
                query=query,
                error="gtn_database_unavailable",
            )

        try:
            message_history = self._extract_message_history(context)
            
            result = await self._run_with_retry(query, message_history=message_history)
            log.info(f"Context: {context}")
            log.info(f"Message history: {message_history}")
            log.info(f"LLM raw response: {result}")
            usage = extract_usage_info(result)
            if usage:
                log.info(
                    "GTN agent token usage: input=%s output=%s total=%s (query_len=%d)",
                    usage.get("input_tokens", 0),
                    usage.get("output_tokens", 0),
                    usage.get("total_tokens", 0),
                    len(query),
                )

            if self._supports_structured_output():
                response_data = extract_structured_output(result, GTNSearchResponse, log)
                if response_data is None:
                    return self._build_response(
                        content=extract_result_content(result),
                        confidence=ConfidenceLevel.LOW,
                        method="text_fallback",
                        result=result,
                        query=query,
                        error="invalid_structured_output",
                    )
                log.info(f"Response data is not None, tutorials found: {response_data}")
                used_fallback = False
                workflow_payloads = self._extract_tool_payloads(result, "search_gtn_workflow_vectors")
                workflow_results = self._workflows_from_vector_payloads(workflow_payloads)
                if workflow_results:
                    existing_workflow_keys = {
                        str(workflow.get("url") or workflow.get("workflow_id") or workflow.get("name") or "")
                        for workflow in response_data.workflows
                    }
                    response_data.workflows.extend(
                        workflow
                        for workflow in workflow_results
                        if str(workflow.get("url") or workflow.get("workflow_id") or workflow.get("name") or "")
                        not in existing_workflow_keys
                    )

                if not response_data.tutorials and not response_data.faqs and not response_data.workflows:
                    log.info("Performing vector search")
                    vector_tutorials = self._search_vector_tutorials_for_response(query)
                    if vector_tutorials:
                        log.info("Vector search successful, found tutorials to use in response")
                        log.info("Found %d tutorials from vector search, using these results", len(vector_tutorials))
                        log.info(f"Vector search tutorials: {vector_tutorials}")
                        used_fallback = True
                        response_data = GTNSearchResponse(
                            tutorials=vector_tutorials,
                            summary=response_data.summary
                            or f"Found {len(vector_tutorials)} GTN tutorial matches from vector search.",
                            learning_path=response_data.learning_path,
                            prerequisites=response_data.prerequisites,
                            total_time=response_data.total_time,
                        )
                should_search_workflows = (
                    not response_data.workflows
                    and (self._looks_like_workflow_query(query) or not response_data.tutorials and not response_data.faqs)
                )
                if should_search_workflows:
                    log.info("Performing workflow vector search")
                    vector_workflows = self._search_vector_workflows_for_response(query)
                    if vector_workflows:
                        used_fallback = True
                        response_data.workflows.extend(vector_workflows)
                        if not response_data.summary:
                            response_data.summary = f"Found {len(vector_workflows)} workflow matches from vector search."
                if not response_data.tutorials and not response_data.faqs and not response_data.workflows:
                    log.info("No tutorials or FAQs in response, falling back to direct search")
                    fallback_results = self.gtn_db.search(query, limit=5)
                    if fallback_results:
                        used_fallback = True
                        response_data = GTNSearchResponse(
                            tutorials=[r.to_dict() for r in fallback_results],
                            summary=f"Found {len(fallback_results)} tutorials related to your query",
                        )

                return self._build_response(
                    content=self._format_gtn_response(response_data),
                    confidence=(
                        ConfidenceLevel.HIGH
                        if response_data.tutorials or response_data.faqs or response_data.workflows
                        else ConfidenceLevel.MEDIUM
                    ),
                    method="structured_with_fallback" if used_fallback else "structured",
                    result=result,
                    query=query,
                    suggestions=self._create_suggestions(response_data),
                    agent_data={
                        "tutorial_count": len(response_data.tutorials),
                        "workflow_count": len(response_data.workflows),
                        "faq_count": len(response_data.faqs),
                        "has_learning_path": bool(response_data.learning_path),
                        "total_time": response_data.total_time,
                    },
                )

            # Simple-text path for backends that don't support structured output.
            response_text = extract_result_content(result)
            parsed_result = self._parse_simple_response(response_text)
            return self._build_response(
                content=parsed_result.get("content", response_text),
                confidence=parsed_result.get("confidence", ConfidenceLevel.MEDIUM),
                method="simple_text",
                result=result,
                query=query,
                suggestions=parsed_result.get("suggestions", []),
                agent_data={"tutorial_count": parsed_result.get("tutorial_count", 0)},
            )

        except (OSError, ValueError) as e:
            log.error(f"GTN training agent error: {e}")
            return self._get_error_response(str(e))

    @staticmethod
    def _result_messages(result: Any) -> list[Any]:
        """Return pydantic-ai run messages across supported result versions."""
        for attr_name in ("all_messages", "new_messages"):
            messages = getattr(result, attr_name, None)
            if not messages:
                continue
            try:
                collected = list(messages()) if callable(messages) else list(messages)
            except (TypeError, ValueError):
                continue
            if collected:
                return collected
        return []

    @staticmethod
    def _json_payload(value: Any) -> Optional[dict[str, Any]]:
        if isinstance(value, dict):
            return value
        if not isinstance(value, str):
            return None
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    @classmethod
    def _extract_tool_payloads(cls, result: Any, tool_name: str) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for message in cls._result_messages(result):
            for part in getattr(message, "parts", []) or []:
                part_tool_name = getattr(part, "tool_name", None)
                if part_tool_name is None and hasattr(part, "model_dump"):
                    try:
                        part_tool_name = part.model_dump().get("tool_name")
                    except (AttributeError, TypeError, ValueError):
                        part_tool_name = None
                if part_tool_name != tool_name:
                    continue
                for attr_name in ("content", "return_value"):
                    payload = cls._json_payload(getattr(part, attr_name, None))
                    if payload:
                        payloads.append(payload)
                if hasattr(part, "model_dump"):
                    try:
                        dumped = part.model_dump()
                    except (AttributeError, TypeError, ValueError):
                        dumped = {}
                    for key in ("content", "return_value"):
                        payload = cls._json_payload(dumped.get(key))
                        if payload:
                            payloads.append(payload)
        return payloads

    @staticmethod
    def _vector_result_to_tutorial(result: dict[str, Any]) -> dict[str, Any]:
        tutorial = dict(result)
        metadata = tutorial.get("metadata")
        if isinstance(metadata, dict):
            for key in ("title", "topic", "tutorial", "url", "difficulty", "time_estimation", "source"):
                if not tutorial.get(key) and metadata.get(key):
                    tutorial[key] = metadata[key]

        tutorial_slug = str(tutorial.get("tutorial") or "").strip()
        title = str(tutorial.get("title") or "").strip()
        if not title:
            title = tutorial_slug.replace("-", " ").title() if tutorial_slug else "GTN Tutorial"
        tutorial["title"] = title
        url = GTNTrainingAgent._tutorial_external_url(tutorial)
        if url:
            tutorial["url"] = url

        if not tutorial.get("snippet"):
            page_content = str(tutorial.get("page_content") or "").strip()
            if page_content:
                tutorial["snippet"] = page_content[:10000]
        tutorial.setdefault("difficulty", "Unknown")
        tutorial.setdefault("time_estimation", "Unknown")
        tutorial.setdefault("result_type", "tutorial")
        return tutorial

    @classmethod
    def _tutorials_from_vector_payloads(cls, payloads: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
        tutorials: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for payload in payloads:
            raw_results = payload.get("tutorials") or payload.get("results") or []
            if not isinstance(raw_results, list):
                continue
            for raw_result in raw_results:
                if not isinstance(raw_result, dict):
                    continue
                tutorial = cls._vector_result_to_tutorial(raw_result)
                key = (
                    str(tutorial.get("topic") or ""),
                    str(tutorial.get("tutorial") or ""),
                    str(tutorial.get("url") or ""),
                )
                if key in seen:
                    continue
                seen.add(key)
                tutorials.append(tutorial)
                if len(tutorials) >= limit:
                    return tutorials
        return tutorials

    @staticmethod
    def _workflow_result_to_response(result: dict[str, Any]) -> dict[str, Any]:
        workflow = dict(result)
        metadata = workflow.get("metadata")
        if isinstance(metadata, dict):
            for key in (
                "workflow_name",
                "name",
                "title",
                "url",
                "topic",
                "source",
                "workflow_id",
                "data_source",
                "doi",
                "updated",
                "path",
                "categories",
                "collections",
                "content_type",
            ):
                if not workflow.get(key) and metadata.get(key):
                    workflow[key] = metadata[key]

        workflow_name = str(
            workflow.get("workflow_name")
            or workflow.get("name")
            or workflow.get("title")
            or workflow.get("workflow_id")
            or ""
        ).strip()
        workflow["workflow_name"] = workflow_name or "Untitled Workflow"
        workflow.setdefault("title", workflow["workflow_name"])

        if not workflow.get("snippet"):
            page_content = str(workflow.get("page_content") or workflow.get("content") or "").strip()
            if page_content:
                workflow["snippet"] = page_content[:10000]

        workflow.setdefault("result_type", "workflow")
        return workflow

    @classmethod
    def _workflows_from_vector_payloads(cls, payloads: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
        workflows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for payload in payloads:
            raw_results = payload.get("workflows") or payload.get("results") or []
            if not isinstance(raw_results, list):
                continue
            for raw_result in raw_results:
                if not isinstance(raw_result, dict):
                    continue
                workflow = cls._workflow_result_to_response(raw_result)
                key = str(
                    workflow.get("url")
                    or workflow.get("workflow_id")
                    or workflow.get("source")
                    or workflow.get("workflow_name")
                    or ""
                )
                if key in seen:
                    continue
                seen.add(key)
                workflows.append(workflow)
                if len(workflows) >= limit:
                    return workflows
        return workflows

    def _search_vector_tutorials_for_response(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        try:
            results = self.gtn_db.search_gtn_vector_db(query=query, embeddings=self.embeddings, persist_dir=self.persist_dir, collection_name="gtn_tutorials", limit=limit)
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            log.warning(f"GTN direct vector fallback failed: {e}")
            return []
        tutorials = []
        for result in results:
            try:
                tutorials.append(self._vector_result_to_tutorial(result.to_dict()))
            except (AttributeError, TypeError, ValueError) as e:
                log.warning(f"Skipping invalid GTN vector fallback result: {e}")
        return tutorials
    
    def _search_vector_workflows_for_response(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        try:
            results = self.gtn_db.search_workflow_vector_db(query=query, embeddings=self.embeddings, persist_dir=self.persist_dir, collection_name="iwc_workflows", limit=limit)
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            log.warning(f"GTN workflow vector fallback failed: {e}")
            return []
        workflows = []
        for result in results:
            try:
                workflow_dict = result.to_dict()
                workflow_dict["result_type"] = "workflow"
                workflows.append(workflow_dict)
            except (AttributeError, TypeError, ValueError) as e:
                log.warning(f"Skipping invalid GTN workflow vector fallback result: {e}")
        return workflows

    @staticmethod
    def _tutorial_external_url(item: dict[str, Any]) -> Optional[str]:
        url = item.get("url")
        if isinstance(url, str) and url.strip() and url.strip() != "#":
            return url.strip()

        topic = str(item.get("topic") or "").strip().strip("/")
        tutorial = str(item.get("tutorial") or "").strip().strip("/")
        if topic and tutorial and topic != "Unknown":
            return f"{GTN_TRAINING_BASE_URL}/topics/{topic.lower()}/tutorials/{tutorial}/tutorial.html"
        return None

    def _format_gtn_response(self, response_data: GTNSearchResponse) -> str:
        parts: list[str] = []
        if response_data.summary:
            parts.append(response_data.summary)

        if response_data.tutorials:
            parts.append("\n**Relevant Tutorials:**")
            for i, tutorial in enumerate(response_data.tutorials, 1):
                title = tutorial.get("title", "Untitled Tutorial")
                topic = tutorial.get("topic", "Unknown")
                difficulty = tutorial.get("difficulty", "Unknown")
                time_estimation = tutorial.get("time_estimation", "Unknown")
                url = self._tutorial_external_url(tutorial)
                snippet = tutorial.get("snippet", "")

                parts.append(f"\n{i}. **{title}**")
                if snippet:
                    parts.append(f"   {snippet}")
                if topic and topic != "Unknown":
                    parts.append(f"   - Topic: {topic}")
                if difficulty and difficulty != "Unknown":
                    parts.append(f"   - Difficulty: {difficulty}")
                if time_estimation and time_estimation != "Unknown":
                    parts.append(f"   - Time: {time_estimation}")
                if url:
                    parts.append(f"   - Link: {url}")

        if response_data.workflows:
            parts.append("\n**Relevant Workflows:**")
            for i, workflow in enumerate(response_data.workflows, 1):
                title = (
                    workflow.get("workflow_name")
                    or workflow.get("name")
                    or workflow.get("title")
                    or workflow.get("workflow_id")
                    or "Untitled Workflow"
                )
                topic = workflow.get("topic", "Unknown")
                url = workflow.get("url")
                snippet = workflow.get("snippet", "")
                data_source = workflow.get("data_source", "")
                doi = workflow.get("doi", "")

                parts.append(f"\n{i}. **{title}**")
                if snippet:
                    parts.append(f"   {snippet}")
                if topic and topic != "Unknown":
                    parts.append(f"   - Topic: {topic}")
                if data_source:
                    parts.append(f"   - Source: {data_source}")
                if doi:
                    parts.append(f"   - DOI: {doi}")
                if url:
                    parts.append(f"   - Link: {url}")

        if response_data.faqs:
            parts.append("\n**Relevant FAQs:**")
            for i, faq in enumerate(response_data.faqs, 1):
                title = faq.get("title", "Untitled FAQ")
                category = faq.get("category", "Unknown")
                area = faq.get("area", "")
                url = self._tutorial_external_url(faq)
                snippet = faq.get("snippet", "")

                parts.append(f"\n{i}. **{title}**")
                if snippet:
                    parts.append(f"   {snippet}")
                if category and category != "Unknown":
                    parts.append(f"   - Category: {category}")
                if area:
                    parts.append(f"   - Area: {area}")
                if url:
                    parts.append(f"   - Link: {url}")

        if response_data.learning_path:
            parts.append(f"\n**Suggested Learning Path:**\n{response_data.learning_path}")

        if response_data.prerequisites:
            parts.append("\n**Prerequisites:**")
            for prereq in response_data.prerequisites:
                parts.append(f"- {prereq}")

        if response_data.total_time:
            parts.append(f"\n**Total Time Investment:** {response_data.total_time}")

        return "\n".join(parts)

    def _create_suggestions(self, response_data: GTNSearchResponse) -> list[ActionSuggestion]:
        suggestions: list[ActionSuggestion] = []

        for tutorial in response_data.tutorials[:3]:
            title = tutorial.get("title", "Untitled Tutorial")
            url = self._tutorial_external_url(tutorial)
            if not url:
                continue
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.VIEW_EXTERNAL,
                    description=f"Open tutorial: {title}",
                    parameters={"url": url},
                    confidence=ConfidenceLevel.HIGH,
                    priority=1,
                )
            )

        for faq in response_data.faqs[:3]:
            title = faq.get("title", "Untitled FAQ")
            url = self._tutorial_external_url(faq)
            if not url:
                continue
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.VIEW_EXTERNAL,
                    description=f"Open FAQ: {title}",
                    parameters={"url": url},
                    confidence=ConfidenceLevel.HIGH,
                    priority=1 if not response_data.tutorials else 2,
                )
            )

        for workflow in response_data.workflows[:3]:
            title = (
                workflow.get("workflow_name")
                or workflow.get("name")
                or workflow.get("title")
                or workflow.get("workflow_id")
                or "Untitled Workflow"
            )
            url = workflow.get("url")
            if not url:
                continue
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.VIEW_EXTERNAL,
                    description=f"Open workflow: {title}",
                    parameters={"url": url},
                    confidence=ConfidenceLevel.HIGH,
                    priority=1 if not response_data.tutorials else 2,
                )
            )

        topics: set[str] = set()
        for t in response_data.tutorials:
            topic = t.get("topic")
            if topic and topic != "Unknown":
                topics.add(topic)
        for topic in list(topics)[:2]:
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.VIEW_EXTERNAL,
                    description=f"Explore more {topic} tutorials",
                    parameters={"url": f"https://training.galaxyproject.org/training-material/topics/{topic.lower()}/"},
                    confidence=ConfidenceLevel.MEDIUM,
                    priority=2,
                )
            )

        return suggestions

    def _get_simple_system_prompt(self) -> str:
        return """
        You are a Galaxy training specialist. Help users find relevant Galaxy Training Network tutorials.

        Respond in this exact format:
        TUTORIALS: [tutorial name 1, tutorial name 2]
        TOPICS: [topic 1, topic 2]
        SUMMARY: [brief summary of recommendations]
        CONFIDENCE: [high/medium/low]

        Example:
        TUTORIALS: Galaxy 101, RNA-seq analysis with Salmon
        TOPICS: Introduction, Transcriptomics
        SUMMARY: For beginners, start with Galaxy 101 to learn the basics, then move to RNA-seq analysis
        CONFIDENCE: high

        Always recommend actual GTN tutorials and provide helpful guidance.
        """

    def _parse_simple_response(self, response_text: str) -> dict[str, Any]:
        # normalize_llm_text handles literal \n that some backends emit instead of real newlines
        normalized_text = normalize_llm_text(response_text)

        tutorials = re.search(r"TUTORIALS:\s*([^\n]+)", normalized_text, re.IGNORECASE)
        topics = re.search(r"TOPICS:\s*([^\n]+)", normalized_text, re.IGNORECASE)
        summary = re.search(r"SUMMARY:\s*([^\n]+)", normalized_text, re.IGNORECASE)
        confidence_match = re.search(r"CONFIDENCE:\s*(\w+)", normalized_text, re.IGNORECASE)

        confidence_level = ConfidenceLevel.MEDIUM
        if confidence_match:
            conf_str = confidence_match.group(1).lower()
            if conf_str == "high":
                confidence_level = ConfidenceLevel.HIGH
            elif conf_str == "low":
                confidence_level = ConfidenceLevel.LOW

        content_parts: list[str] = []
        if summary and summary.group(1).strip():
            content_parts.append(summary.group(1).strip())
        if tutorials and tutorials.group(1).strip():
            content_parts.append(f"\n**Recommended Tutorials:**\n{tutorials.group(1).strip()}")
        if topics and topics.group(1).strip():
            content_parts.append(f"\n**Related Topics:** {topics.group(1).strip()}")
        content_parts.append(
            "\n**Note:** Visit https://training.galaxyproject.org/training-material/ to access all tutorials."
        )
        if not content_parts:
            content_parts = [response_text]

        suggestions: list[ActionSuggestion] = []
        if tutorials and tutorials.group(1).strip() and self.gtn_db:
            for tutorial_name in [t.strip() for t in tutorials.group(1).split(",")][:3]:
                results = self.gtn_db.search(tutorial_name, limit=1)
                if results:
                    result = results[0]
                    suggestions.append(
                        ActionSuggestion(
                            action_type=ActionType.VIEW_EXTERNAL,
                            description=f"Open tutorial: {result.title}",
                            parameters={"url": result.url},
                            confidence=confidence_level,
                            priority=1,
                        )
                    )

        if not suggestions:
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.VIEW_EXTERNAL,
                    description="Visit Galaxy Training Network",
                    parameters={"url": "https://training.galaxyproject.org/training-material/"},
                    confidence=confidence_level,
                    priority=1,
                )
            )

        return {
            "content": "\n".join(content_parts),
            "confidence": confidence_level,
            "tutorial_count": len(tutorials.group(1).split(",")) if tutorials and tutorials.group(1).strip() else 0,
            "suggestions": suggestions,
        }

    def _get_fallback_content(self) -> str:
        return (
            "I couldn't search the training materials at this moment. "
            "You can browse tutorials directly at: "
            "https://training.galaxyproject.org/training-material/"
        )

    def _get_error_response(self, error_message: str) -> AgentResponse:
        return self._build_response(
            content=f"I encountered an error while searching training materials: {error_message}\n\n"
            f"You can browse tutorials directly at: https://training.galaxyproject.org/training-material/",
            confidence=ConfidenceLevel.LOW,
            method="error_fallback",
            suggestions=[
                ActionSuggestion(
                    action_type=ActionType.VIEW_EXTERNAL,
                    description="Visit Galaxy Training Network",
                    parameters={"url": "https://training.galaxyproject.org/training-material/"},
                    confidence=ConfidenceLevel.HIGH,
                    priority=1,
                )
            ],
            error=error_message,
        )
