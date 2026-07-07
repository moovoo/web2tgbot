FROM ghcr.io/astral-sh/uv:python3.13-trixie
ARG dev
RUN if [ -z $dev ]; then apt-get update && apt-get install -y ffmpeg; fi

WORKDIR /app

RUN groupadd -g 65530 runner && useradd -u 65530 -g 65530 --create-home --shell /bin/bash runner
RUN chown runner:runner -R /app && chmod go+rwx /app
USER runner

COPY --chown=runner:runner pyproject.toml uv.lock ./
RUN uv sync --no-cache $([ -z "$dev" ] && echo "--no-dev --group prod")

USER root
RUN uv run playwright install --with-deps && rm -rf /root/.cache
USER runner
RUN uv run --no-dev cloakbrowser install && uv run --no-dev cloakbrowser info

COPY --chown=runner:runner . /app/

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
