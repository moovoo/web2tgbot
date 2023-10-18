FROM python:3.10
ARG dev
RUN if [ -z $dev ]; then apt-get update && apt-get install -y ffmpeg; fi

COPY requirements.txt requirements.dev.txt ./
RUN pip install -r requirements.txt
RUN if [ $dev ]; then pip install -r requirements.dev.txt; fi
WORKDIR /app
COPY ./ /app/

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
