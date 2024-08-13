FROM amd64/python:3.10.8-bullseye

COPY requirements.txt ./

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .
COPY ./docker_entrypoint.sh ./docker_entrypoint.sh

RUN ["chmod", "+x", "./docker_entrypoint.sh"]

ENTRYPOINT ["./docker_entrypoint.sh"]