FROM python:3.13-slim-bookworm@sha256:a1165e272e578941b84abc79e4ab38a0305cd12803a5c4247979ac7655f4d641
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/inference_adapter.py /app/inference_adapter.py
USER 10001:10001
EXPOSE 8098
CMD ["python", "/app/inference_adapter.py"]
