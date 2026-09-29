# Tool State

A tool's parameter values travel through Galaxy in several representations, each modelled by a
`ToolState` subclass in `galaxy.tool_util.parameters.state`. Each subclass pairs the raw
`input_state` dictionary with the pydantic model used to validate it.

## State Representations

Every representation subclasses `ToolState` and sets its `state_representation`. The arrows are the
conversions between them, named after the functions in `galaxy.tool_util.parameters.convert`.

```{mermaid}
flowchart LR
    relaxed["RelaxedRequestToolState<br/>relaxed_request"]
    request["RequestToolState<br/>request"]
    request_internal["RequestInternalToolState<br/>request_internal"]
    dereferenced["RequestInternalDereferencedToolState<br/>request_internal_dereferenced"]
    job_internal["JobInternalToolState<br/>job_internal"]
    job_runtime["JobRuntimeToolState<br/>job_runtime"]
    landing["LandingRequestToolState<br/>landing_request"]
    landing_internal["LandingRequestInternalToolState<br/>landing_request_internal"]
    test_case["TestCaseToolState<br/>test_case_xml"]
    test_case_json["TestCaseJsonToolState<br/>test_case_json"]
    workflow_step["WorkflowStepToolState<br/>workflow_step"]
    workflow_step_linked["WorkflowStepLinkedToolState<br/>workflow_step_linked"]

    relaxed -- strictify --> request
    request -- decode --> request_internal
    request_internal -- dereference --> dereferenced
    dereferenced -- expand --> job_internal
    landing -- landing_decode --> landing_internal
    workflow_step -- preprocess links and defaults --> workflow_step_linked
```

- **Request** states reference datasets as `{src: "hda", id: <encoded_id>}` and allow mapping and
  reduction constructs. The relaxed variant also accepts the looser legacy tool input syntax, and
  `strictify` converts it into a strict request.
- **Request internal** states use decoded ids and may still contain URI `src` dictionaries.
  Dereferencing turns those URIs into HDAs.
- **Job internal** states have mapping constructs expanded out, one state per job.
- **Test case** states reference files by name or URI and do not allow mapping constructs.
- **Workflow step** states make nearly everything optional except conditional discriminators. The
  linked variant brings in the step's connections and defaults so they can be validated too.

## Submitting a Job Through the API

```{mermaid}
sequenceDiagram
    participant apireq as API Request
    participant api as Jobs API
    participant service as Job Service
    participant database as Database
    participant queue as TaskQueue

    apireq->>api: HTTP JSON
    api->>service: create()
    service->>service: If not strict, build and verify RelaxedRequestToolState
    service->>service: If not strict, strictify() RelaxedRequestToolState into RequestToolState
    service->>service: If strict, build and validate RequestToolState from request
    service->>service: decode() RequestToolState into RequestInternalToolState
    service->>database: Serialize RequestInternalToolState
    service->>queue: Queue QueueJobs with reference to persisted RequestInternalToolState
    service->>api: JobCreateResponse (pydantic model)
    api->>apireq: JobCreateResponse (as JSON)
```

## Queuing the Jobs

```{mermaid}
sequenceDiagram
    participant queue as TaskQueue
    participant task as queue_jobs Task
    participant queue_jobs as JobSubmitter.queue_jobs
    participant dereference as JobSubmitter.dereference
    participant materialize_task as materialize Task
    participant handle_input as Tool.handle_input_async
    participant expand as expand_meta_parameters_async
    participant tool_action as ToolAction.execute

    queue->>task: Launch task
    task->>queue_jobs: QueueJobs pydantic model
    queue_jobs->>dereference: RequestInternalToolState
    dereference->>queue_jobs: RequestInternalDereferencedToolState
    queue_jobs->>materialize_task: HDA (with state deferred)
    materialize_task->>queue_jobs: Return when state is okay
    queue_jobs->>handle_input: RequestInternalDereferencedToolState
    handle_input->>expand: RequestInternalDereferencedToolState
    expand->>handle_input: JobInternalToolState[]
    loop over expanded job tool states
        handle_input->>tool_action: JobInternalToolState
        tool_action->>handle_input: A Galaxy job
    end
```
