==========
Deployment
==========

The service consists of a main web and celery worker docker container
and supporting services.

In a production environment the following services are typically used:

- Amazon ELB handling SSL termination
- Amazon EC2 running Docker containers for both web and worker roles
- Amazon ElastiCache Redis
- Amazon RDS Postgres
- Amazon S3
- Nginx running on the web role EC2 instances, proxying HTTP traffic
- A Datadog/StatsD daemon running on each EC2 instance
- An externally hosted Sentry service


Docker Image
============

The service is built upon a single docker image, which is shared between
the web and worker roles.

The image contains an entrypoint which can take either "web" or "worker"
as the run command, defaulting to "web".

It exposes port 8000, which is only used by the web role.


Environment Variables
=====================

The docker image expects to get the app configuration via environment
variables.

Both roles expect:

* ``PUBLIC_KEY``, example ``LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0K\n...``
* ``REDIS_HOST``, example ``example.cache.amazonaws.com``
* ``SENTRY_DSN``, example ``https://public:secret@sentry.example.com/id``
* ``STATSD_HOST``, example ``172.17.42.1``

The worker role additionally expects:

* ``DB_HOST``, example ``example.rds.amazonaws.com``
* ``DB_NAME``, example ``miracle``
* ``DB_USER``, example ``miracle``
* ``DB_PASSWORD``, example ``secret``
* ``PRIVATE_KEY``, example ``LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCg==...``

The ``PRIVATE_KEY`` and ``PUBLIC_KEY`` are both base64 encoded versions
of PEM files. So the private key should start with
``-----BEGIN PRIVATE KEY-----\n`` before being base64 encoded and the
public key should start with ``-----BEGIN PUBLIC KEY-----`` before being
base64 encoded.


Database Setup
==============

Database setup and migrations are handled by alembic. The docker image
exposes the "alembic" script as a command.

The alembic command takes the database configuration from the environment,
so you need to pass on all required `DB_*` variables and call the command
via:

.. code-block:: bash

    docker run -e "DB_HOST=..." -e "DB_..." -it <image id> alembic [arguments]

Get help for the available arguments:

.. code-block:: bash

    docker ... alembic -h

Setup the initial database structure:

.. code-block:: bash

    docker ... alembic stamp base
    docker ... alembic upgrade head

Inspect the available migrations and the current database revision:

.. code-block:: bash

    docker ... alembic history
    docker ... alembic current

Upgrade to the latest revision:

.. code-block:: bash

    docker ... alembic upgrade head

Downgrade to a previous revision:

.. code-block:: bash

    docker ... alembic downgrade <revision id>

Or by going back a number of steps, e.g. two:

.. code-block:: bash

    docker ... alembic downgrade -2


AWS Permissions
===============

Both roles expect to have access from inside the Docker containers
to the ElastiCache Redis instance, the Sentry and the StatsD daemon.

Only the worker role should have access to the RDS Postgres instance
from inside the docker container.


Web Role Configuration
======================

The HTTP/S flow generally is:

Internet --> ELB --> Nginx --> Web Server inside Docker Container

The docker container exposes the web server on port 8000 and it can
be bound at runtime to port 8000 on the EC2 host machine.

Typically an Nginx instance on the EC2 host will listen on port
80 and 443 for HTTP traffic and proxy pass both to port 8000.

The ELB listens on port 80 for HTTP and port 443 for HTTPS traffic
and handles SSL termination. It forwards both as HTTP-only traffic
to Nginx on port 80 and 443 respectively.

The ELB should use health checks and can use the ``/__lbheartbeat__``
endpoint supported by the application to do so.


Status Checks
=============

Both roles will try to connect to Redis during app startup, and send
an error report to Sentry if they fail.

The worker role will also try to connect to the Postgres database and
send an error to Sentry if it fails.

The web role exposes three URL endpoints to check its status:

* ``__lbheartbeat__`` - Returns 200 OK if the web app is responding.
* ``__heartbeat__`` - Returns 200 OK if the web app can connect to services.
* ``__version__`` - Returns version data about the running software.
