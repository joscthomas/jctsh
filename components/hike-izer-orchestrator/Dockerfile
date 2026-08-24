# CARD-0086 stage 2 needs the anthropic + paho-mqtt pip packages, unlike
# fetch_hike_data.py's stdlib-only design -- python:3.12-alpine alone (as
# used for stage 1) can't cover that, hence a real build here.
FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# app.py/generation.py/narrative.py/templating.py/mqtt_log.py/ha_notify.py/
# photo_captions.py/place_context.py/cost_tracking.py/birdnet.py/
# wildlife_life_list.py are this component's own source.
# fetch_hike_data.py/fetch_hike_photos.py/build_calendar_index.py/
# build_hike_map.py/build_hike_chart.py/build_wildlife_index.py/
# xeno_canto.py and SKILL.md are deployed copies from components/hike-izer/
# and .claude/skills/hike-izer/ respectively (scp'd into this directory
# before `docker compose build`, not duplicated in the repo -- see this
# component's README for the exact deploy commands). build_hike_map.py/
# build_hike_chart.py added CARD-0134 -- same "deployed copy" treatment as
# fetch_hike_data.py/fetch_hike_photos.py, not this component's own code.
# ha_notify.py added CARD-0141 (Pixel push notifications, same best-effort
# convention as mqtt_log.py). wildlife_life_list.py/build_wildlife_index.py
# added CARD-0142 (cross-hike wildlife life list). xeno_canto.py added
# CARD-0174 (reference-call speaker icon) -- imported by both templating.py
# and build_wildlife_index.py, same "deployed copy, shared by both" pattern
# build_wildlife_index.py itself already used for wikipedia_url().
# open_kanban_pr.py added CARD-0173 (voice-idea webhook, /webhook/idea in
# app.py) -- deployed copy from tos/ (CARD-0191 moved it there from
# core/maintenance/, its original "new source directory for this
# Dockerfile's deployed-copy family" home; every prior deployed copy came
# from components/hike-izer/), same open_finding_pr() this repo's other
# maintenance-check scripts already use to open placeholder kanban PRs.
# build_battery_trend_index.py added CARD-0207 (battery discharge-rate
# trend page) -- same "deployed copy from components/hike-izer/" pattern
# as build_calendar_index.py/build_wildlife_index.py, computation lives in
# fetch_hike_data.py's compute_stats()/_battery_window_crossing_min().
COPY app.py generation.py narrative.py templating.py mqtt_log.py ha_notify.py \
     photo_captions.py place_context.py cost_tracking.py birdnet.py \
     wildlife_life_list.py \
     fetch_hike_data.py fetch_hike_photos.py build_calendar_index.py \
     build_hike_map.py build_hike_chart.py build_wildlife_index.py \
     build_battery_trend_index.py \
     xeno_canto.py open_kanban_pr.py SKILL.md \
     /app/

CMD ["python3", "/app/app.py"]
