FROM sha256:291caba4e1782fd6138638de304153f3542b5b87a81343ee0a46084d2914fd11 AS trusted
USER root
RUN mkdir /candidate /protected && cp -a /buggy/. /candidate/ && find /candidate -type d \( -name tests -o -name test -o -name __pycache__ \) -prune -exec rm -rf '{}' + && rm -f /candidate/.git /candidate/bug_patch.txt
RUN cp -a /buggy/. /protected/ && rm -f /protected/.git
FROM python:3.8.20-slim-bookworm@sha256:1d52838af602b4b5a831beb13a0e4d073280665ea7be7f69ce2382f29c5a613f AS candidate
COPY --from=trusted /usr/local /usr/local
COPY --from=trusted /usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu
COPY --from=trusted /candidate /candidate
ENV PYTHONDONTWRITEBYTECODE=1
USER 65534:65534
WORKDIR /tmp
FROM candidate AS verifier
USER root
COPY --from=trusted /protected /protected
USER 65534:65534
WORKDIR /tmp
