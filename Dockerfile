# VYAYAM on Hugging Face Spaces (Docker SDK). See DEPLOY_HF.md.
# Python version matches runtime.txt (3.12.3).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# opencv-contrib-python (pulled in by mediapipe) needs libGL + glib.
# libmediapipe.so links libEGL + libGLESv2 (checked with objdump on the wheel).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libegl1 libgles2 \
    && rm -rf /var/lib/apt/lists/*

# HF runs Spaces as uid 1000.
RUN useradd -m -u 1000 user
WORKDIR /app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .
RUN chmod +x entrypoint.sh && chown user:user /app && mkdir -p /app/media && chown user:user /app/media

USER user

# settings.py fails fast without DJANGO_SECRET_KEY. This dummy is used only for
# collectstatic and is NOT stored in the image ENV. The real key comes from the
# Space's runtime secrets.
ARG DJANGO_SECRET_KEY=build-only-dummy-key-not-used-at-runtime
RUN DJANGO_SECRET_KEY="$DJANGO_SECRET_KEY" DJANGO_DEBUG=False python manage.py collectstatic --no-input

EXPOSE 7860
CMD ["./entrypoint.sh"]
