FROM --platform=linux/amd64 python:3.12.4-slim@sha256:a074fac67aa01841fee592d00bae14d25dcaf98ef6e12a683ecceb7e0147e2d1
RUN groupadd --gid 65532 sandbox && useradd --uid 65532 --gid 65532 --no-create-home sandbox
COPY --chown=65532:65532 runner.py /runner/runner.py
USER 65532:65532
WORKDIR /sandbox
ENTRYPOINT ["python", "-I", "-S", "/runner/runner.py"]
