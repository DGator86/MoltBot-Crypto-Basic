FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir fastapi uvicorn pydantic pyyaml ccxt
ENV PYTHONPATH=/app/packages
EXPOSE 8001
CMD ["uvicorn", "trading_core.main:app", "--host", "0.0.0.0", "--port", "8001"]
