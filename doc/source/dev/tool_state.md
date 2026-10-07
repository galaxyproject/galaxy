# Tool State

A tool's parameter values travel through Galaxy in several representations, each modelled by a
`ToolState` subclass in `galaxy.tool_util.parameters.state`. Each subclass pairs the raw
`input_state` dictionary with the pydantic model used to validate it.

## State Representations

Every representation subclasses `ToolState` and sets its `state_representation`. The arrows are the
conversions between them, labelled with the function that performs each one.

```{mermaid}
flowchart TB
    subgraph requests ["Tool requests"]
        relaxed["RelaxedRequestToolState<br/><code>relaxed_request</code>"]
        request["RequestToolState<br/><code>request</code>"]
        request_internal["RequestInternalToolState<br/><code>request_internal</code>"]
        dereferenced["RequestInternalDereferencedToolState<br/><code>request_internal_dereferenced</code>"]
    end
    subgraph jobs ["Jobs"]
        job_internal["JobInternalToolState<br/><code>job_internal</code>"]
        job_runtime["JobRuntimeToolState<br/><code>job_runtime</code>"]
    end
    subgraph tests ["Tool tests"]
        test_case["TestCaseToolState<br/><code>test_case_xml</code>"]
        test_case_json["TestCaseJsonToolState<br/><code>test_case_json</code>"]
    end
    subgraph workflows ["Workflows"]
        workflow_step["WorkflowStepToolState<br/><code>workflow_step</code>"]
        workflow_step_linked["WorkflowStepLinkedToolState<br/><code>workflow_step_linked</code>"]
    end
    subgraph landing_requests ["Landing requests"]
        landing["LandingRequestToolState<br/><code>landing_request</code>"]
        landing_internal["LandingRequestInternalToolState<br/><code>landing_request_internal</code>"]
    end

    relaxed -- strictify --> request
    request -- decode --> request_internal
    request_internal -- dereference --> dereferenced
    dereferenced -- expand_meta_parameters_async --> job_internal
    job_internal -- runtimeify --> job_runtime
    test_case -- encode_test --> request
    request_internal -- to_workflow_step_state --> workflow_step_linked
    landing -- landing_decode --> landing_internal
    job_runtime ~~~ landing
```

- **Request** states reference datasets as `{src: "hda", id: <encoded_id>}` and allow mapping and
  reduction constructs. The relaxed variant also accepts the looser legacy tool input syntax, and
  `strictify` converts it into a strict request.
- **Request internal** states use decoded ids and may still contain URI `src` dictionaries.
  Dereferencing turns those URIs into HDAs.
- **Job internal** states have mapping constructs expanded out, one state per job. **Job runtime**
  states replace dataset references with the JSON a running job sees.
- **Test case** states reference files by name or URI and do not allow mapping constructs. XML
  tool tests produce `test_case_xml` states, YAML tool tests `test_case_json` ones.
- **Workflow step** states make nearly everything optional except conditional discriminators. The
  linked variant replaces data and collection references with connection markers, since workflows
  represent those inputs as connections.
- **Landing request** states hold the pre-filled tool form values of a landing request.

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
