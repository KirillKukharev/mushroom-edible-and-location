#FROM python:3.8-slim-buster
FROM python:3.8

COPY requirements.txt /app/requirements.txt

WORKDIR /app

COPY . ./

#RUN python -m pip install -r requirements.txt
RUN pip3 install -r requirements.txt

RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6  -y

#ENV PYTHONUNBUFFERED True
#ENV WORKERS 2
#ENV THREADS 1

#CMD exec gunicorn --bind :$PORT --workers $WORKERS --threads $THREADS --timeout 0 app:app

CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]