import os
import time

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
