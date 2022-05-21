
# Message queue

Galaxy uses a message queue internally for communicating between processes. 
This is powered by the [Kombu MQ library](https://docs.celeryq.dev/projects/kombu/). 
For example, when reloading the toolbox or locking job execution,
the process that handled that particular request will tell all others to also reload, lock jobs, etc. 

<!-- TODO Discuss Galaxies benefit of using an MQ -->

<!-- TODO the types of messages being passed, more detailed than above -->

This is configured via the [amqp_internal_connection](https://docs.galaxyproject.org/en/latest/admin/config.html#amqp-internal-connection)
option in `galaxy.yml`. For connection examples, see the [Kombu connection documentation](https://docs.celeryq.dev/projects/kombu/en/stable/userguide/connections.html).
See the [URL specification](https://docs.celeryq.dev/projects/kombu/en/stable/userguide/connections.html#urls) on that page for more information on configuring different transports.

<!-- TODO copy in an actual rabbit MQ example from the link above 
```
amqp_internal_connection: 
```
-->

By default, Galaxy will first attempt to use
your specified [database_connection](https://docs.galaxyproject.org/en/latest/admin/config.html#database-connection).  
If that's not specified either, Galaxy will automatically create and use a separate SQLite
database located in your <galaxy>/database folder.

## Transports
Kombu and Galaxy support a variety of MQ transport/server options. 
[RabbitMQ](https://www.rabbitmq.com/) via AMQP is the most popular for production deployments.

Visit the [Kombu reference index](https://docs.celeryq.dev/projects/kombu/en/stable/reference/index.html) for a
complete list of supported transports and their configuration.

<!-- TODO Specify any requirements Galaxy has for transport features. -->

<!-- TODO Specify what nodes need to be able to access the MQ (nginx proxy, web and job handlers, workflow schedulers, compute nodes, etc?). -->
