# Dockerfile for polarrouteserver, intended for development use only

FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=polarrouteserver.settings.development

RUN pip install --upgrade pip

WORKDIR /usr/src/app

COPY --chmod=775 entrypoint.sh .

COPY pyproject.toml manage.py /usr/src/app/
COPY polarrouteserver /usr/src/app/polarrouteserver

RUN pip install .