FROM python:3.13-slim-bookworm@sha256:a1165e272e578941b84abc79e4ab38a0305cd12803a5c4247979ac7655f4d641

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y bash=5.2.15-2+b13 git=1:2.39.5-0+deb12u3 \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /workspace \
    && chown 10003:10003 /workspace

WORKDIR /app
COPY services/workspace_runner.py /app/workspace_runner.py
USER 10003:10003
EXPOSE 8091
CMD ["python", "/app/workspace_runner.py"]
