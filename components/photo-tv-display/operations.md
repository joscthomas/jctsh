# photo-tv-display — Operations

## Service status / restart / logs

```bash
ssh jct@m8.local
sudo systemctl status photo-tv-display
sudo systemctl restart photo-tv-display
journalctl -u photo-tv-display -f
```

## Updating dependencies

```bash
ssh jct@m8.local
cd ~/photo-tv-display
npm outdated
npm update
sudo systemctl restart photo-tv-display
```

## Deploying a code change

Always edit in the repo first (source of truth), then:

```bash
scp <changed files> jct@m8.local:~/photo-tv-display/<path>
ssh jct@m8.local "sudo systemctl restart photo-tv-display"
```

## Manually starting the slideshow without the phone controller

```bash
curl -X POST http://m8.local:3000/api/start-slideshow
```

## Rotating credentials

If `IMMICH_API_KEY_JOSEPH`/`_ROBIN` or `HA_LONG_LIVED_TOKEN` are ever rotated
(shared with other components — see root `CLAUDE.md`'s Credentials section),
update `~/photo-tv-display/.env` on the M8 and restart the service. This
component does not have its own dedicated HA token or MQTT account (no MQTT
involvement at all — see Phase 2 planning's "Why Not Node-RED").

## Known open item: idle-detection thresholds

`routes/homeassistant.js`'s `IDLE_STATES` list is a documented placeholder
until Joseph observes the real states `media_player.groom_tv` reports (see
`testing.md`). If the idle auto-start ever behaves wrong (fires too
early/late, or never fires), start there.
