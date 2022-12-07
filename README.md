
# Boost Library Stats

A set of scripts to sync github pull requests and issues to a local Postgres database, and generate "views" to display the information per boost library.

https://boost-library-stats.cpp.al

## Instructions

Run `collect_stats.py` as a cron task:

```
0 5 1 * * . $HOME/.web-env-vars && cd $HOME/boost_library_stats && ./scripts/collect_stats.py > /tmp/boost-library-stats.output 2>&1
```

Store credentials in /home/stats/.web-env-vars, load as environment variables:

```
export DATABASE_USER=
export DATABASE_PASSWORD=
export DATABASE_NAME=
export DATABASE_HOST=
export DATABASE_PORT=
export SECRET_KEY=
export DJANGO_SETTINGS_MODULE='boost_library_stats.settings'
export RESTMOTE_USER=
export RESTMOTE_PASSWORD=
