import os
import sys
import time
import subprocess
import logging


logger = logging.getLogger("runestone")
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s: %(asctime)s:  %(funcName)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


from celery import Celery


celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)


@celery.task(bind=True, name="create_task")
def create_task(self, task_type):
    num = int(task_type)  # 1, 2, or 3
    for i in range(num):
        self.update_state(state="PROGRESS", meta={"current": i, "total": num})
        time.sleep(10)
    return True


# update state - https://www.distributedpython.com/2018/09/28/celery-task-states/#:~:text=The%20update_state%20method.%20The%20Celery%20task%20object%20provides,define%20your%20own%20state%20is%20a%20unique%20name.

# new worker
# 1. pull from github for the given repo
# 2. build
# 3. Update the _static (for ptx)
# 4. process manifest (for ptx)
# 5. Update the library
@celery.task(bind=True, name="clone_runestone_book")
def clone_runestone_book(self, repo, bcname):
    self.update_state(state="CLONING", meta={"step": "clone"})
    logger.debug(f"Running clone command for {repo}")
    cwd = os.getcwd()
    try:
        res = subprocess.run(
            f"git clone {repo}", shell=True, capture_output=True, cwd="/books"
        )
        if res.returncode != 0:
            err = res.stderr.decode("utf8")
            logger.debug(f"ERROR: {err}")
            self.update_state(state="FAILED", meta={"current": err[:20]})
            return False
    except:
        self.update_state(state="FAILED", meta={"step": "clone"})
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


@celery.task(bind=True, name="build_runestone_book")
def build_runestone_book(self, book):
    self.update_state(state="CHECKING", meta={"step": "clone"})
    res = subprocess.run(
        f"git pull", shell=True, capture_output=True, cwd=f"/books/{book}"
    )
    if res.returncode != 0:
        return False

    res = subprocess.run(
        f"pretext build runestone",
        shell=True,
        capture_output=True,
        cwd=f"/books/{book}",
    )
    res = subprocess.run(
        f"runestone build --all deploy",
        shell=True,
        capture_output=True,
        cwd=f"/books/{book}",
    )
