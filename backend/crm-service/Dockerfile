FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
EXPOSE 4002
CMD ["python", "manage.py", "runserver", "0.0.0.0:4002"]
