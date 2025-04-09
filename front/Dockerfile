FROM python:3.11

WORKDIR /app
RUN pip install setuptools --upgrade
RUN pip install wheel uwsgi
ADD ./requirements.txt /app/requirements.txt

RUN pip install -r requirements.txt
ADD ./src /app

ADD run_app.sh /app/run_app.sh
RUN chmod +x /app/run_app.sh 

CMD ["/app/run_app.sh"]
