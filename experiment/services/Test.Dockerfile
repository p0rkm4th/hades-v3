FROM python:3.13-slim-bookworm@sha256:a1165e272e578941b84abc79e4ab38a0305cd12803a5c4247979ac7655f4d641

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY tests/ /app/tests/
COPY contracts/tools.json /app/tools.json
USER 10002:10002
CMD ["python", "-m", "unittest", "discover", "-s", "/app/tests"]
