FROM python:3.10

RUN apt-get update && apt-get install -y ffmpeg

COPY requirements.txt .
RUN pip install -r requirements.txt

WORKDIR /app
COPY ./ /app/

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
