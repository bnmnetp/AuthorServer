# ***********************************
# |docname| - Celery Worker Functions
# ***********************************
# Use celery worker functions for long running processes like building a book.
#
#
# Imports
# =======
# These are listed in the order prescribed by `PEP 8`_.
#
# Standard library
# ----------------
import datetime
import os
import sys
import time
import subprocess
import logging
import pathlib
from models import Session, auth_user, courses, Book, BookAuthor
from sqlalchemy import update

# Third Party
# -----------
from celery import Celery

# Local Application
# -----------------
from runestone.server.utils import _build_runestone_book, _build_ptx_book


# Set up logging

logger = logging.getLogger("runestone")
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s: %(asctime)s:  %(funcName)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


# Because we are reusing many functions also used by `rsmanage` to do various build tasks
# I wanted a way to have the click status messages come back to the web UI.  So,
# we will pass in our own version of click.echo to these functions that
# uses the status functions of celery workers.
# update state - https://www.distributedpython.com/2018/09/28/celery-task-states/#:~:text=The%20update_state%20method.%20The%20Celery%20task%20object%20provides,define%20your%20own%20state%20is%20a%20unique%20name.
class MyClick:
    def __init__(self, worker, state):
        self.worker = worker
        self.state = state
        logger.debug(f"MyClick worker is {self.worker}")

    def echo(self, message):
        logger.debug(f"UPDATE State: {self.state} {message}")
        self.worker.update_state(state=self.state, meta={"current": message})


# Mock the click config object. It is only used for dburl information in this context
class Config:
    def __init__(self):
        conf = os.environ.get("WEB2PY_CONFIG", "production")
        if conf == "production":
            self.dburl = os.environ.get("DBURL")
        elif conf == "development":
            self.dburl = os.environ.get("DEV_DBURL")
        elif conf == "test":
            self.dburl = os.environ.get("TEST_DBURL")
        else:
            print("Incorrect WEB2PY_CONFIG")


config = Config()

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)

# new worker
# 1. pull from github for the given repo
# 2. build
# 3. Update the _static (for ptx)
# 4. process manifest (for ptx)
# 5. Update the library


@celery.task(bind=True, name="clone_runestone_book")
def clone_runestone_book(self, repo, bcname):
    self.update_state(state="CLONING", meta={"current": "cloning"})
    logger.debug(f"Running clone command for {repo}")
    cwd = os.getcwd()
    try:
        res = subprocess.run(
            ["git", "clone", repo, bcname], capture_output=True, cwd="/books"
        )
        outputlog = pathlib.Path("/books", bcname, "buildlog.txt")
        with open(outputlog, "w") as olfile:
            olfile.write(res.stdout)
            olfile.write("\n====\n")
            olfile.write(res.stderr)
        if res.returncode != 0:
            err = res.stderr.decode("utf8")
            logger.debug(f"ERROR: {err}")
            self.update_state(state="FAILED", meta={"current": err[:20]})
            return False
    except:
        self.update_state(state="FAILED", meta={"current": "failed"})
        return False

    # check the name of the repo move the top level file
    os.chdir("/books")
    dirs = os.listdir()
    if bcname not in dirs:
        self.update_state(state="RENAMING", meta={"step": "clone"})
        repo_parts = repo.split("/")
        folder = repo_parts[-1].replace(".git", "").strip()
        os.rename(folder, bcname)

    # Add the base course to the database

    return True


def update_last_build(book):
    stmt = (
        update(Book)
        .where((Book.document_id == book))
        .values(last_build=datetime.datetime.utcnow())
    )
    with Session.begin() as session:
        session.execute(stmt)


@celery.task(bind=True, name="build_runestone_book")
def build_runestone_book(self, book):
    logger.debug(f"Building {book}")
    self.update_state(state="CHECKING", meta={"current": "pull latest"})
    res = subprocess.run(["git", "pull"], capture_output=True, cwd=f"/books/{book}")
    if res.returncode != 0:
        return False

    myclick = MyClick(self, "BUILDING")
    self.update_state(state="BUILDING", meta={"current": "running build"})
    os.chdir(f"/books/{book}")
    res = _build_runestone_book(book, click=myclick)
    if res:
        self.update_state(state="FINISHING", meta={"current": "changing permissions"})
    else:
        self.update_state(state="BUILDING", meta={"current": "Build failed -- see log"})

    res = subprocess.run(
        f"chgrp -R www-data .", shell=True, capture_output=True, cwd=f"/books/{book}"
    )
    if res.returncode != 0:
        return False
    res = subprocess.run(
        f"chmod -R go+rw .", shell=True, capture_output=True, cwd=f"/books/{book}"
    )
    if res.returncode != 0:
        return False
    self.update_state(state="SUCCESS", meta={"current": "build complete"})
    update_last_build(book)
    return True


@celery.task(bind=True, name="build_ptx_book")
def build_ptx_book(self, book):
    logger.debug(f"Building {book}")
    self.update_state(state="CHECKING", meta={"current": "pull latest"})
    res = subprocess.run(
        f"git pull", shell=True, capture_output=True, cwd=f"/books/{book}"
    )
    if res.returncode != 0:
        return False

    os.chdir(f"/books/{book}")
    logger.debug(f"Before building myclick self = {self}")
    myclick = MyClick(self, "PTXBUILD")
    logger.debug("Starting build")
    res = _build_ptx_book(config, False, "runestone-manifest.xml", book, click=myclick)
    if res:
        self.update_state(state="FINISHING", meta={"current": "updating permissions"})
    else:
        self.update_state(state="BUILDING", meta={"current": "Failed - see log"})
        return False

    res = subprocess.run(
        f"chgrp -R www-data .", shell=True, capture_output=True, cwd=f"/books/{book}"
    )
    if res.returncode != 0:
        return False
    res = subprocess.run(
        f"chmod -R go+rw .", shell=True, capture_output=True, cwd=f"/books/{book}"
    )
    if res.returncode != 0:
        return False

    self.update_state(state="SUCCESS", meta={"current": "build complete"})
    update_last_build(book)
    return True


# This task requires you to have an ssh keypair set up, and when you build the container
# you will need to make sure to copy the key into /usr/src/app/
@celery.task(bind=True, name="deploy_book")
def deploy_book(self, book):
    logger.debug(f"Deploying {book}")
    user = "bmiller"
    self.update_state(state="STARTING", meta={"current": "pull latest"})
    numServers = int(os.environ["NUM_SERVERS"].strip())

    for i in range(1, numServers + 1):
        command = f"rsync -e 'ssh -oStrictHostKeyChecking=no -i /usr/src/app/.ssh/id_rsa'  --exclude '__pycache__' -P -rzc /books/{book} {user}@server{i}:~/Runestone/books --copy-links --delete"
        logger.debug(command)
        self.update_state(state="DEPLOYING", meta={"current": f"server{i}"})
        res = subprocess.run(
            command,
            shell=True,
            capture_output=True,
        )
        if res.returncode != 0:
            logger.debug(res.stdout)
            logger.debug(res.stderr)
            return False
    self.update_state(state="SUCCESS", meta={"current": f"deploy complete"})
    return True
