# pull official base image
FROM python:3.9-bullseye

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN apt update
RUN apt install -y git texlive-full xsltproc pdf2svg
RUN pip install -r requirements.txt

# copy project
COPY . .
