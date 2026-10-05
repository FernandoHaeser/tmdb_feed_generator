FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 FEED_OUT=/feed

# Unprivileged user; /feed is the volume shared with the web container.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin feed \
    && mkdir /feed && chown feed /feed

WORKDIR /app
COPY tmdb_feed_generator ./tmdb_feed_generator
COPY clients ./clients

USER feed
CMD ["python", "-m", "tmdb_feed_generator", "run"]
