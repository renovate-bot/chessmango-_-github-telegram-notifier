FROM docker.io/python:3.11.3-alpine3.17

COPY app/* /

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "github-telegram-notifier.py"]
