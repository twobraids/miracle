from celery import Celery
from celery.app import app_or_default
from celery.signals import (
    worker_process_init,
    worker_process_shutdown,
)
from kombu import Queue

from miracle.bloom import create_bloom_domain
from miracle.cache import create_cache
from miracle.crypto import create_crypto
from miracle.db import create_db
from miracle.config import REDIS_URI
from miracle.log import (
    configure_logging,
    create_raven,
    create_stats,
)


CELERY_QUEUES = (
    Queue('celery_default', routing_key='celery_default'),
    Queue('celery_delete', routing_key='celery_delete'),
    Queue('celery_upload', routing_key='celery_upload'),
)


def configure_celery(celery_app):
    celery_app.config_from_object('miracle.worker.settings')
    celery_app.conf.update(
        BROKER_URL=REDIS_URI,
        CELERY_RESULT_BACKEND=REDIS_URI,
        CELERY_QUEUES=CELERY_QUEUES,
    )


def init_worker(celery_app,
                _bloom_domain=None, _cache=None,
                _crypto=None, _db=None, _raven=None, _stats=None):
    configure_logging()
    raven = create_raven(transport='threaded', _raven=_raven)

    try:
        celery_app.bloom_domain = create_bloom_domain(_bloom=_bloom_domain)
        celery_app.cache = create_cache(_cache=_cache)
        celery_app.crypto = create_crypto(_crypto=_crypto)
        celery_app.db = create_db(_db=_db)
        celery_app.raven = raven
        celery_app.stats = create_stats(_stats=_stats)

        celery_app.cache.ping(raven)
        celery_app.db.ping(raven)
    except Exception:  # pragma: no cover
        raven.captureException()
        raise


def shutdown_worker(celery_app):
    celery_app.bloom_domain.close()
    del celery_app.bloom_domain
    celery_app.cache.close()
    del celery_app.cache
    del celery_app.crypto
    celery_app.db.close()
    del celery_app.db
    del celery_app.raven
    celery_app.stats.close()
    del celery_app.stats


@worker_process_init.connect
def init_worker_process(signal, sender, **kw):  # pragma: no cover
    # get the app in the current forked worker process
    celery_app = app_or_default()
    init_worker(celery_app)


@worker_process_shutdown.connect
def shutdown_worker_process(signal, sender, **kw):  # pragma: no cover
    # get the app in the current forked worker process
    celery_app = app_or_default()
    shutdown_worker(celery_app)


celery_app = Celery('miracle.worker.app')
configure_celery(celery_app)
