FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY app.py berkeley.py node.py ./
COPY static/ ./static/
COPY tests/ ./tests/
USER 10001:10001
EXPOSE 8000
STOPSIGNAL SIGINT
CMD ["python", "app.py", "--host", "0.0.0.0", "--no-browser"]
