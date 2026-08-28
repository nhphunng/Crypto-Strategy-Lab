FROM python:3.12.4-slim@sha256:a3e58f9399353be051735f09be0316bfdeab571a5c6a24fd78b92df85bcb2d85
RUN groupadd --gid 65532 sandbox && useradd --uid 65532 --gid 65532 --no-create-home sandbox
COPY --chown=65532:65532 runner.py /runner/runner.py
USER 65532:65532
WORKDIR /sandbox
ENTRYPOINT ["python", "-I", "-S", "/runner/runner.py"]
