# CARD-0086 stage 2 needs the anthropic + paho-mqtt pip packages, unlike
# fetch_hike_data.py's stdlib-only design -- python:3.12-alpine alone (as
# used for stage 1) can't cover that, hence a real build here.
FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# app.py/generation.py/narrative.py/templating.py/mqtt_log.py/
# photo_captions.py/place_context.py/cost_tracking.py/birdnet.py are this
# component's own source. fetch_hike_data.py/fetch_hike_photos.py/
# build_calendar_index.py/build_hike_map.py/build_hike_chart.py and
# SKILL.md are deployed copies from components/hike-izer/ and
# .claude/skills/hike-izer/ respectively (scp'd into this directory before
# `docker compose build`, not duplicated in the repo -- see this
# component's README for the exact deploy commands). build_hike_map.py/
# build_hike_chart.py added CARD-0134 -- same "deployed copy" treatment as
# fetch_hike_data.py/fetch_hike_photos.py, not this component's own code.
COPY app.py generation.py narrative.py templating.py mqtt_log.py \
     photo_captions.py place_context.py cost_tracking.py birdnet.py \
     fetch_hike_data.py fetch_hike_photos.py build_calendar_index.py \
     build_hike_map.py build_hike_chart.py SKILL.md \
     /app/

CMD ["python3", "/app/app.py"]
