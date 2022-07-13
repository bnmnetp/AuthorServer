# Author Server

Give authors on Runestone Academy control of rebuilding and deploying their books.

Using FastAPI, Celery, Redis, and docker to manage background tasks. Thanks to Michael Herman for the [excellent article](https://testdriven.io/blog/fastapi-and-celery/) that got me started on this project.

### Quick Start

Spin up the containers:

```sh
$ docker-compose up -d --build
```

Open your browser to [http://localhost:8004](http://localhost:8004)
