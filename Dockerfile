FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && addgroup --system batax && adduser --system --ingroup batax batax
COPY --chown=batax:batax . .
RUN mkdir -p /app/staticfiles /app/run && chown -R batax:batax /app/staticfiles /app/run
USER batax
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
