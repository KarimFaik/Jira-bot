FROM python:3.12.7

WORKDIR /app

COPY . .

RUN python -m pip install --upgrade pip && pip install -r requirements.txt

ENTRYPOINT [ "python3", "app_Main.py" ]
