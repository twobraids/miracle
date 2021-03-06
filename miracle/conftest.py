import gc
import warnings

from alembic import command
import pytest
from sqlalchemy import (
    inspect,
)
from sqlalchemy import text
import webtest

from miracle.bloom import create_bloom_domain
from miracle.cache import create_cache
from miracle.config import ALEMBIC_CFG
from miracle.crypto import create_crypto
from miracle.db import create_db
from miracle.log import (
    create_raven,
    create_stats,
)
from miracle.models import Model
from miracle.web.app import (
    create_app,
    shutdown_app,
)
from miracle.worker.app import (
    celery_app,
    init_worker,
    shutdown_worker,
)


def setup_db(engine):
    with engine.connect() as conn:
        # Create all tables from model definition.
        trans = conn.begin()
        Model.metadata.create_all(engine)
        trans.commit()
    # Finally stamp the database with the latest alembic version.
    command.stamp(ALEMBIC_CFG, 'head')


def teardown_db(engine):
    inspector = inspect(engine)
    with engine.connect() as conn:
        # Drop all tables currently in the database.
        trans = conn.begin()
        table_names = inspector.get_table_names()
        for table_name in table_names:
            conn.execute(text('DROP TABLE "%s" CASCADE' % table_name))
        trans.commit()


@pytest.fixture(scope='session', autouse=True)
def package():
    # Apply gevent monkey patches as early as possible during tests.
    from gevent.monkey import patch_all
    patch_all()
    from psycogreen.gevent import patch_psycopg
    patch_psycopg()

    # Enable all warnings in test mode.
    warnings.resetwarnings()
    warnings.simplefilter('default')

    # Look for memory leaks.
    gc.set_debug(gc.DEBUG_UNCOLLECTABLE)

    yield None

    # Print memory leaks.
    if gc.garbage:  # pragma: no cover
        print('Uncollectable objects found:')
        for obj in gc.garbage:
            print(obj)


@pytest.fixture(scope='session')
def bloom_domain():
    bloom = create_bloom_domain()
    yield bloom
    bloom.close()


@pytest.fixture(scope='session')
def global_cache():
    cache = create_cache()
    yield cache
    cache.close()


@pytest.fixture(scope='function')
def cache(global_cache):
    yield global_cache
    global_cache.flushdb()


@pytest.fixture(scope='session')
def crypto():
    crypto = create_crypto()
    yield crypto


@pytest.fixture(scope='session')
def global_db():
    db = create_db()
    teardown_db(db.engine)
    setup_db(db.engine)
    yield db
    db.close()


@pytest.fixture(scope='function')
def cleanup_db():
    db = create_db()
    yield db
    teardown_db(db.engine)
    setup_db(db.engine)
    db.close()


@pytest.fixture(scope='function')
def db(global_db):
    with global_db.engine.connect() as conn:
        with conn.begin() as trans:
            global_db.session_factory.configure(bind=conn)
            yield global_db
            global_db.session_factory.configure(bind=None)
            trans.rollback()


@pytest.fixture(scope='session')
def global_raven():
    raven = create_raven()
    yield raven


@pytest.fixture(scope='function')
def raven(global_raven):
    yield global_raven
    messages = [msg['message'] for msg in global_raven.msgs]
    global_raven.clear()
    assert not messages


@pytest.fixture(scope='session')
def global_stats():
    stats = create_stats()
    yield stats
    stats.close()


@pytest.fixture(scope='function')
def stats(global_stats):
    yield global_stats
    global_stats.clear()


@pytest.fixture(scope='session')
def global_celery(bloom_domain, crypto, global_cache,
                  global_db, global_raven, global_stats):
    init_worker(
        celery_app,
        _bloom_domain=bloom_domain,
        _cache=global_cache,
        _crypto=crypto,
        _db=global_db,
        _raven=global_raven,
        _stats=global_stats)
    yield celery_app
    shutdown_worker(celery_app)


@pytest.fixture(scope='function')
def celery(global_celery, cache, db, raven, stats):
    yield global_celery


@pytest.fixture(scope='session')
def global_app(crypto, global_cache, global_celery,
               global_raven, global_stats):
    wsgiapp = create_app(
        _cache=global_cache,
        _crypto=crypto,
        _raven=global_raven,
        _stats=global_stats)
    app = webtest.TestApp(wsgiapp)
    yield app
    shutdown_app(app.app)


@pytest.fixture(scope='function')
def app(global_app, cache, celery, raven, stats):
    yield global_app
