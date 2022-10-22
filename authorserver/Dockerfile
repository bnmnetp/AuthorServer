# pull official base image
FROM python:3.9-bullseye

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN pip install --upgrade pip
RUN apt update
RUN apt install -y --fix-missing git texlive-full xsltproc pdf2svg rsync sagemath
#RUN pip install -r requirements.txt
#RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
RUN pip install poetry

# copy project
COPY . .
COPY .ssh/id_rsa .
RUN /usr/local/bin/poetry install
