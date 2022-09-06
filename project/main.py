# ****************************************
# |docname| - web ui endponits for authors
# ****************************************
#
#
# Imports
# =======
# These are listed in the order prescribed by `PEP 8`_.
#
# Standard library
# ----------------
import os
import pathlib
import datetime

# third party
# -----------
import aiofiles
from fastapi import Body, FastAPI, Form, Request, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from celery.result import AsyncResult
from sqlalchemy import create_engine, Table, MetaData, select, and_, or_
from sqlalchemy.orm.session import sessionmaker
from fastapi_login import LoginManager

# Local App
# ---------
from worker import (
    build_runestone_book,
    clone_runestone_book,
    build_ptx_book,
    deploy_book,
)
from models import Session, auth_user, courses, Book, BookAuthor
from authorImpact import get_enrollment_graph, get_pv_heatmap

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

auth_manager = LoginManager("supersecret", "/auth/validate", use_cookie=True)
auth_manager.cookie_name = "access_token"


@auth_manager.user_loader()  # type: ignore
def _load_user(user_id: str):
    """
    fetch a user object from the database. This is designed to work with the
    original web2py auth_user schema but make it easier to migrate to a new
    database by simply returning a user object.
    """

    return fetch_user(user_id)


def fetch_user(user_id: str):
    # Create an AuthUser object from the databae metadata
    sel = select([auth_user]).where(auth_user.c.username == user_id)
    with Session() as sess:
        res = sess.execute(sel).first()
        # res is a SqlAlchemy Row - you can access columns by position or by name
        print(f"RES = {res}")
        return res


def fetch_books_by_author(author: str):
    query = (
        select(Book, BookAuthor)
        .join(BookAuthor, BookAuthor.book == Book.document_id)
        .where(BookAuthor.author == author)
    )
    with Session() as sess:
        res = sess.execute(query).fetchall()
        return res


def create_book_entry(author: str, document_id: str, github: str):
    new_book = Book(
        document_id=document_id,
        github_url=github,
        last_build=datetime.datetime.utcnow(),
    )
    new_ba = BookAuthor(author=author, book=document_id)
    with Session.begin() as session:
        session.add(new_book)
        session.add(new_ba)


# Install the auth_manager as middleware This will make the user
# part of the request ``request.state.user`` `See FastAPI_Login Advanced <https://fastapi-login.readthedocs.io/advanced_usage/>`_
auth_manager.useRequest(app)


@app.get("/")
async def home(request: Request, user=Depends(auth_manager)):
    print(f"{request.state.user} OR user = {user}")

    if user:
        if not verify_author(user):
            return RedirectResponse(url="/notauthorized")

    if user:
        name = user.first_name
        book_list = fetch_books_by_author(user.username)

    else:
        name = "unknown person"
        book_list = []
        # redirect them back somewhere....

    return templates.TemplateResponse(
        "home.html", context={"request": request, "name": name, "book_list": book_list}
    )


def verify_author(user):
    with Session() as sess:
        auth_row = sess.execute(
            """select * from auth_group where role = 'author'"""
        ).first()
        auth_group_id = auth_row[0]
        is_author = sess.execute(
            f"""select * from auth_membership where user_id = {user.id} and group_id = {auth_group_id}"""
        ).first()
    return is_author


@app.get("/impact/{book}")
def impact(request: Request, book: str, user=Depends(auth_manager)):
    # check for author status
    if user:
        if not verify_author(user):
            return RedirectResponse(url="/notauthorized")
    else:
        return RedirectResponse(url="/notauthorized")

    resGraph = get_enrollment_graph(book)
    chapterHM = get_pv_heatmap(book)
    return templates.TemplateResponse(
        "impact.html",
        context={"request": request, "enrollData": resGraph, "chapterData": chapterHM},
    )

@app.get("/subchapmap/{chapter}/{book}")
    def impact(request: Request, chapter: str, book: str, user=Depends(auth_manager)):
        # check for author status
        if user:
            if not verify_author(user):
                return RedirectResponse(url="/notauthorized")
        else:
            return RedirectResponse(url="/notauthorized")
    
        chapterHM = get_subchap_heatmap(book)
        return templates.TemplateResponse(
            "impact.html",
            context={"request": request, "enrollData": resGraph, "chapterData": chapterHM},
        )


@app.get("/getlog/{book}")
async def getlog(request: Request, book):
    logpath = pathlib.Path("/books", book, "cli.log")

    if logpath.exists():
        async with aiofiles.open(logpath, "rb") as f:
            result = await f.read()
            result = result.decode("utf8")
    else:
        result = "No logfile found"
    return JSONResponse({"detail": result})


@app.get("/notauthorized")
def not_authorized(request: Request):
    return templates.TemplateResponse(
        "notauthorized.html", context={"request": request}
    )


@app.post("/book_in_db")
async def check_db(payload=Body(...)):
    base_course = payload["bcname"]
    # connect to db and check if book is there and if base_course == course_name
    if "DEV_DBURL" not in os.environ:
        return JSONResponse({"detail": "DBURL is not set"})
    else:
        sel = select([courses]).where(courses.c.course_name == base_course)
        with Session() as sess:
            res = sess.execute(sel).first()
            detail = res["id"] if res else False
            return JSONResponse({"detail": detail})


@app.post("/add_course")
async def new_course(payload=Body(...), user=Depends(auth_manager)):
    base_course = payload["bcname"]
    github_url = payload["github"]
    if "DEV_DBURL" not in os.environ:
        return JSONResponse({"detail": "DBURL is not set"})
    else:
        engine = create_engine(os.environ["DEV_DBURL"])
        res = engine.execute(
            f"""insert into courses
           (course_name, base_course, python3, term_start_date, login_required, institution, courselevel, downloads_enabled, allow_pairs, new_server)
                values ('{base_course}',
                '{base_course}',
                'T',
                '2022-01-01',
                'F',
                'Runestone',
                '',
                'F',
                'F',
                'T')
                """
        )
        create_book_entry(user.username, base_course, github_url)
        if res:
            return JSONResponse({"detail": "success"})
        else:
            return JSONResponse({"detail": "fail"})


@app.post("/clone", status_code=201)
async def do_clone(payload=Body(...)):
    repourl = payload["url"]
    bcname = payload["bcname"]
    task = clone_runestone_book.delay(repourl, bcname)
    return JSONResponse({"task_id": task.id})


@app.post("/isCloned", status_code=201)
async def check_repo(payload=Body(...)):
    bcname = payload["bcname"]
    repo_path = pathlib.Path("/books", bcname)
    if repo_path.exists():
        return JSONResponse({"detail": True})
    else:
        return JSONResponse({"detail": False})


@app.post("/buildBook", status_code=201)
async def do_build(payload=Body(...)):
    bcname = payload["bcname"]
    rstproj = pathlib.Path("/books") / bcname / "pavement.py"
    ptxproj = pathlib.Path("/books") / bcname / "project.ptx"
    if ptxproj.exists():
        book_system = "PreTeXt"
    else:
        book_system = "Runestone"
    if book_system == "Runestone":
        task = build_runestone_book.delay(bcname)
    else:
        task = build_ptx_book.delay(bcname)

    return JSONResponse({"task_id": task.id})


@app.post("/deployBook", status_code=201)
async def do_deploy(payload=Body(...)):
    bcname = payload["bcname"]
    task = deploy_book.delay(bcname)
    return JSONResponse({"task_id": task.id})


# Called from javascript to get the current status of a task
#
@app.get("/tasks/{task_id}")
async def get_status(task_id):
    task_result = AsyncResult(task_id)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result,
    }
    return JSONResponse(result)
