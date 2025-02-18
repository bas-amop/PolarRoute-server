# Deployment
For production, the following are required:

+ Access to a RabbitMQ server, (can use `make start-rabbitmq` to start one in a docker container)
+ Celery and celery beat servers running,
+ WSGI server, e.g. Gunicorn, mod_wsgi (httpd)

For serving with Gunicorn, run `make start-django-server` to serve with WSGI and production settings.

## Management of a deployment

All of the commands used for administration of a Django project are available post-installation via the `django-admin` command.

Of particular interest in production are:

```shell
$ django-admin makemigrations # create new migrations files based on changes to models
$ django-admin migrate # apply new migrations files to alter the database
$ django-admin dbshell # open the database's command line interface
```

To see more commands, run `django-admin --help`.

In addition a custom command is available to manually insert new meshes into the database from file:

```shell
$ django-admin insert_mesh <Mesh file or list of files>
```

`insert_mesh` takes a filename or list of filepaths containing meshes either as `.vessel.json` format or gzipped vessel mesh files.

Only meshes which are not present in the database will be inserted. Uniqueness is based on the md5 hash of the unzipped vessel mesh file.
