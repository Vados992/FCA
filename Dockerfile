ARG FCEA_PYTHON_IMAGE=python:3.12-slim-bookworm
FROM ${FCEA_PYTHON_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FCEA_DATA_DIR=/data
WORKDIR /app
RUN groupadd --gid 10001 fcea && useradd --uid 10001 --gid 10001 --no-create-home fcea && mkdir /data && chown 10001:10001 /data
COPY --chown=10001:10001 fcea /app/fcea
COPY LICENSE NOTICE /app/
USER 10001:10001
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3).read()"
ENTRYPOINT ["python", "-m", "fcea"]
CMD ["serve", "--host", "0.0.0.0", "--allow-remote"]
