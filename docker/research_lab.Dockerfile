FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir fastapi uvicorn requests beautifulsoup4
ENV PYTHONPATH=/app/packages
EXPOSE 8002
CMD ["uvicorn", "research_lab.main:app", "--host", "0.0.0.0", "--port", "8002"]
