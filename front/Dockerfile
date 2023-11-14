FROM ubuntu:22.04

RUN pip3 install mininet wheel uwsgi

WORKDIR /app
ADD ./requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt
ADD ./ENTRYPOINT.sh /app/ENTRYPOINT.sh
RUN chmod +x /app/ENTRYPOINT.sh
ADD flask /app

ENTRYPOINT ["/app/ENTRYPOINT.sh"]

FROM python:3.11

WORKDIR /app
RUN pip install wheel uwsgi
ADD ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
ADD . /app

CMD ["uwsgi", "--ini", "/app/uwsgi.ini"]
