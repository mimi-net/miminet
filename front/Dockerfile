FROM python:3.11

WORKDIR /app
RUN pip install wheel uwsgi
ADD ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
ADD . /app

CMD ["uwsgi", "--ini", "/app/uwsgi.ini"]
