# How SQLAlchemy sessions are handled in Galaxy

## Access to the Session object registry

We have a central resource from which to grab the Session object registry [see sessionmaker in the SQLAlchemy documentation](https://docs.sqlalchemy.org/en/20/orm/session_api.html#sqlalchemy.orm.sessionmaker), that is `app.model.session`.
You can either use it directly as a proxy to the current session or call `app.model.session()` to get the proxied Session object, or use the context manager (e.g. `with app.model.session() as session:`), as detailed in the SQLAlchemy documentation.

## Session object registry scopes

The default scope of the Session object registry is [thread local](https://docs.sqlalchemy.org/en/20/orm/contextual.html#thread-local-scope). This means that accessing a Session through the Session object registry will return the same Session in the same thread. This default scope can be changed if necessary.

### WSGI, ASGI, Celery

In the context of the web app (WSGI and ASGI) there is a clearly delineated lifespan for a session, and that lifespan isn't tied to a thread. The scope of the Session object registry is set at the beginning of a web request using `app.model.set_request_id(request_id)`. At the end of a web request we remove the scope using `app.model.unset_request_id(request_id)`. This also closes and removes any active Session object. Similarly, we set the scope for each Celery task execution using `set_request_id` and `unset_request_id`.

By using this mechanism we are certain that web requests and celery tasks receive a new Session object and that any resources held by the session are released.

### Job and Workflow handlers

Job and Workflow handlers perform multiple pieces of business logic in separate threads and care needs to be taken when deciding when to start a transaction, when to do a rollback and if and where a session lifespan can be introduced.

The following paragraph discusses the choices made in <https://github.com/galaxyproject/galaxy/blob/064360dab053426ce166bb7274d6a3a5790eb7cc/lib/galaxy/jobs/runners/__init__.py#L835-L843>:

The `JobHandlerQueue.monitor` method is executed as a thread within the job handler process,
and all work that requires access to the database is happening inside `check_watched_items`,
which iterates over jobs assigned to this handler process. By setting the scope to a new,
random uuid around `check_watched_items` we ensure that even if the session becomes corrupt
the session is properly discarded and the next iteration of `check_watched_items` receives
a new, clean session to work with. As the work within `JobHandlerQueue.monitor` is happening within a single thread it is not technically necessary to set a custom scope, and one could simply call `app.model.session.close`; however, there is very little cost associated to setting a custom scope and it becomes very clear
where the session lifespan starts and ends.

As a guiding principle an attempt should be made to manage the session state and database-related exception handling as high up in the calling stack as possible.
