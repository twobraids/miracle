#!/bin/sh

cd $(dirname $0)
case "$1" in
    web)
        echo "Starting Web Server"
        exec ./web.sh
        ;;
    worker)
        echo "Starting Celery Worker"
        exec ./worker.sh
        ;;
    shell)
        echo "Opening shell"
        cd ..
        exec /bin/sh
        ;;
    test)
        echo "Running Tests"
        cd ..
        TESTING=true pytest --cov-config=.coveragerc --cov=miracle miracle && \
            flake8 miracle
        ;;
    alembic)
        echo "Running Alembic"
        cd ..
        alembic $2 $3 $4 $5 $6 $7 $8 $9
        ;;
    bloom)
        echo "Running Bloom"
        cd ..
        miracle_bloom $2 $3 $4 $5 $6 $7 $8 $9
        # Wait around, so one can copy the archive from the container.
        sleep 120
        ;;
    *)
        echo "Usage: $0 {web|worker|shell|test|alembic}"
        exit 1
esac
