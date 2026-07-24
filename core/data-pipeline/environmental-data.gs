// Google Apps Script — JCTsh Environmental Data
// Spreadsheet: "JCTsh Environmental Data"
// Repo: core/data-pipeline/environmental-data.gs
//
// To deploy: paste this entire file into the Apps Script editor (Extensions → Apps Script),
// then Deploy → Manage deployments → pencil → Version: New version → Save.
// The deployment URL does not change on redeployment.
//
// API_KEY is stored in Script Properties (Project Settings → Script Properties).
// The same key is stored in Node-RED environment variables and credentials.local.md.
//
// SCRIPT_VERSION below exists purely to make it easy to confirm a redeploy actually
// took effect — bump it whenever this file changes. Returned in every doGet response
// (including the "unknown action" fallback) so a version mismatch is visible from a
// plain curl call, not just by eyeballing the editor.

var SCRIPT_VERSION = '2026-07-24.2-hike-start-forecast-datefix';

// ---------------------------------------------------------------------------
// doPost — environmental sensor data (Node-RED → Sheets)
// ---------------------------------------------------------------------------
// Routes incoming sensor payloads to the correct sheet based on payload.component.
// Called by the Node-RED wildcard data handler for every jctsh/components/+/data message.

function doPost(e) {
  try {
    var expectedKey = PropertiesService.getScriptProperties().getProperty('API_KEY');
    if (!expectedKey || e.parameter.key !== expectedKey) {
      return ContentService
        .createTextOutput(JSON.stringify({status: 'error', message: 'unauthorized'}))
        .setMimeType(ContentService.MimeType.JSON);
    }

    var payload = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();

    if (payload.component === 'hiking-observations') {
      var obsSheet = ss.getSheetByName('Hiking Observations');

      var obsText = (payload.observation || '').trim();

      // Category keyword scan — assigns all matching categories
      var taxonomy = {
        'vegetation':  ['saguaro','bloom','cactus','tree','shrub','flower','plant','grass','palo verde','ocotillo'],
        'wildlife':    ['bird','hawk','coyote','snake','rabbit','deer','javelina','lizard','butterfly','insect'],
        'weather':     ['cloud','rain','wind','storm','thunder','lightning','temperature','hot','cold','warm','cool'],
        'visibility':  ['clear','hazy','smoke','dust','fog','smoggy','murky'],
        'sky':         ['moon','sun','stars','sunrise','sunset','rainbow','shadow'],
        'air_quality': ['smoky','dusty','smell','odor','particulate','ash'],
        'trail':       ['trail','path','wash','ridge','peak','summit','canyon','rock','boulder','erosion'],
        'subjective':  ['feels','seems','appears','noticed','unusual','different','surprising']
      };
      var lower = obsText.toLowerCase();
      var categories = [];
      for (var cat in taxonomy) {
        var keywords = taxonomy[cat];
        for (var k = 0; k < keywords.length; k++) {
          if (lower.indexOf(keywords[k]) !== -1) {
            categories.push(cat);
            break;
          }
        }
      }

      // Normalize timestamp — accept ISO string or Unix epoch seconds integer
      var ts = payload.ts;
      if (typeof ts === 'number' || /^\d{1,10}$/.test(String(ts))) {
        ts = new Date(Number(ts) * 1000).toISOString();
      }

      var obsCoords = _gpsLookup(ss, ts);
      obsSheet.appendRow([ts, obsText, JSON.stringify(categories), payload.source || 'voice', obsCoords.lat, obsCoords.lon]);

      // CARD-0083: capture the weather forecast on the first observation of a
      // new Arizona-local calendar day -- a live snapshot of what was
      // forecast right as the hike began, written once and never re-fetched.
      _maybeCaptureHikeStartForecast(ss, ts, obsCoords);

    } else {
      var envSheet = ss.getSheetByName('Environmental Data');
      var v = function(field) {
        var val = payload[field];
        return (val !== undefined && val !== null) ? val : '';
      };
      envSheet.appendRow([
        v('ts'),              // A  timestamp
        v('source'),          // B  source
        v('lat'),             // C  lat
        v('lon'),             // D  lon
        v('temp_f'),          // E  temp_f
        v('humidity_pct'),    // F  humidity_pct
        v('pressure_hpa'),    // G  pressure_hpa
        v('dew_point_f'),     // H  dew_point_f
        v('heat_index_f'),    // I  heat_index_f
        v('uv_index'),        // J  uv_index
        v('irradiance_wm2'),  // K
        v('wind_speed_mph'),  // L
        v('wind_dir_deg'),    // M
        v('rain_tips'),       // N
        v('rainin'),          // O
        v('dailyrainin'),     // P
        v('battery_v'),       // Q
        v('rssi_dbm'),        // R
        v('pm1_ug_m3'),       // S
        v('pm25_ug_m3'),      // T
        v('pm4_ug_m3'),       // U
        v('pm10_ug_m3'),      // V
        v('voc_index'),        // W
        v('nox_index'),        // X
        v('illuminance_lx'),  // Y
        v('solar_v')          // Z
      ]);
    }

    return ContentService
      .createTextOutput(JSON.stringify({status: 'ok'}))
      .setMimeType(ContentService.MimeType.JSON);

  } catch(err) {
    return ContentService
      .createTextOutput(JSON.stringify({status: 'error', message: err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// ---------------------------------------------------------------------------
// onOpen — custom menu
// ---------------------------------------------------------------------------

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('JCTsh')
    .addItem('Refresh Timeline', 'refreshTimeline')
    .addToUi();
}

// ---------------------------------------------------------------------------
// refreshTimeline — merge Environmental Data + Hiking Observations → Timeline
// ---------------------------------------------------------------------------
// Run from the JCTsh menu after a hike to build a unified time-sorted view.
// Timeline columns: timestamp_az | type | summary | categories | lat | lon

function refreshTimeline() {
  var ss           = SpreadsheetApp.getActiveSpreadsheet();
  var envSheet     = ss.getSheetByName('Environmental Data');
  var obsSheet     = ss.getSheetByName('Hiking Observations');
  var timelineSheet = ss.getSheetByName('Timeline');
  if (!timelineSheet) timelineSheet = ss.insertSheet('Timeline');

  var rows = [];

  // Environmental Data (row 0 = header, skip it)
  var envData = envSheet.getDataRange().getValues();
  for (var i = 1; i < envData.length; i++) {
    var r = envData[i];
    if (!r[0]) continue;
    var tsDate = new Date(r[0]);
    if (isNaN(tsDate.getTime())) continue;

    var parts = [];
    if (r[4] !== '') parts.push(Number(r[4]).toFixed(1) + '°F');
    if (r[5] !== '') parts.push(Number(r[5]).toFixed(1) + '% hum');
    if (r[9] !== '') parts.push('UV ' + Number(r[9]).toFixed(1));
    if (r[16] !== '') parts.push(Number(r[16]).toFixed(2) + 'V');
    if (Number(r[17]) === 0) parts.push('field');

    rows.push([tsDate, _azString(tsDate), 'sensor', parts.join(' · '), '', r[2] || null, r[3] || null]);
  }

  // Hiking Observations (row 0 = header, skip it)
  var obsData = obsSheet.getDataRange().getValues();
  for (var j = 1; j < obsData.length; j++) {
    var o = obsData[j];
    if (!o[0]) continue;
    var oDate = new Date(o[0]);
    if (isNaN(oDate.getTime())) continue;

    rows.push([oDate, _azString(oDate), 'observation', o[1], o[2], o[4] || null, o[5] || null]);
  }

  // Sort by UTC timestamp
  rows.sort(function(a, b) { return a[0] - b[0]; });

  // Write to Timeline sheet — drop sort key (col 0)
  timelineSheet.clearContents();
  timelineSheet.getRange(1, 1, 1, 6).setValues([['timestamp_az', 'type', 'summary', 'categories', 'lat', 'lon']]);
  if (rows.length > 0) {
    var output = rows.map(function(r) { return [r[1], r[2], r[3], r[4], r[5], r[6]]; });
    timelineSheet.getRange(2, 1, output.length, 6).setValues(output);
  }

  SpreadsheetApp.getUi().alert('Timeline refreshed — ' + rows.length + ' rows.');
}

// ---------------------------------------------------------------------------
// _azString — format a UTC Date as Arizona local time string (UTC-7, no DST)
// ---------------------------------------------------------------------------

function _azString(utcDate) {
  var az = new Date(utcDate.getTime() - 7 * 60 * 60 * 1000);
  var p  = function(n) { return n < 10 ? '0' + n : String(n); };
  return az.getFullYear() + '-' + p(az.getMonth()+1) + '-' + p(az.getDate()) +
         ' ' + p(az.getHours()) + ':' + p(az.getMinutes()) + ':' + p(az.getSeconds());
}

// ---------------------------------------------------------------------------
// _gpsLookup — shared helper used by doGet(action=lookup) and doPost(hiking-observations)
// ---------------------------------------------------------------------------
// Returns {lat, lon} of the nearest GPS trackpoint within ±5 minutes of tsISO,
// or {lat: null, lon: null} if GPS Track is empty or no match within the window.

function _gpsLookup(ss, tsISO) {
  var gpsSheet = ss.getSheetByName('GPS Track');
  if (!gpsSheet) return {lat: null, lon: null};
  var data = gpsSheet.getDataRange().getValues();
  if (data.length <= 1) return {lat: null, lon: null};

  var targetTime = new Date(tsISO).getTime();
  var fiveMin    = 5 * 60 * 1000;
  var bestRow    = null;
  var bestDiff   = Infinity;

  for (var i = 1; i < data.length; i++) {
    var diff = Math.abs(targetTime - new Date(data[i][0]).getTime());
    if (diff < bestDiff) { bestDiff = diff; bestRow = data[i]; }
  }

  return (bestDiff <= fiveMin && bestRow !== null)
    ? {lat: bestRow[1], lon: bestRow[2]}
    : {lat: null, lon: null};
}

// ---------------------------------------------------------------------------
// _maybeCaptureHikeStartForecast -- CARD-0083
// ---------------------------------------------------------------------------
// Called from doPost's hiking-observations branch on every observation. Only
// actually captures a forecast on the first observation of a new Arizona-
// local calendar day (self-provisioning "Hike Start Forecast" sheet acts as
// its own dedup log). Provider is Open-Meteo (api.open-meteo.com) -- free,
// no API key, and its hourly forecast includes temp/humidity/precip
// probability/wind/UV in one call. Open-Meteo has no named "nearest station"
// concept (unlike NWS/METAR, which snaps to an airport or gridpoint office)
// -- it's a gridded model interpolated to the exact coordinate requested, so
// the response's own lat/lon (the actual grid point used) is stored, not the
// input coordinates, recording precisely what point the forecast was for.
//
// Deliberately does NOT fall back to a hardcoded home-area location when the
// observation has no GPS correlation yet -- that would silently report the
// wrong location's weather for a hike that isn't near home. Skips capture
// for this observation instead; a later observation the same day with a
// resolved GPS position will retry, since "already captured today?" is only
// true once a row has actually been written.
function _maybeCaptureHikeStartForecast(ss, tsISO, coords) {
  try {
    if (coords.lat === null || coords.lon === null) return;

    var dateAz = _azString(new Date(tsISO)).slice(0, 10); // YYYY-MM-DD

    var forecastSheet = ss.getSheetByName('Hike Start Forecast');
    if (!forecastSheet) {
      forecastSheet = ss.insertSheet('Hike Start Forecast');
      forecastSheet.appendRow([
        'timestamp', 'date_az', 'lat', 'lon',
        'temp_f', 'precip_pct', 'wind_mph', 'humidity_pct', 'uv_index', 'provider'
      ]);
    }
    // Force column B (date_az) to plain text. Sheets silently auto-detects a
    // bare "YYYY-MM-DD" string as a real Date value on write, which breaks
    // the dedup comparison below -- a stored Date object never string-equals
    // a freshly computed "YYYY-MM-DD" string, so every observation would
    // re-trigger a capture instead of just the first one each day. Applied
    // unconditionally (not just on sheet creation) so it's also safe against
    // a sheet that already exists from before this fix.
    forecastSheet.getRange('B:B').setNumberFormat('@');

    var existing = forecastSheet.getDataRange().getValues();
    for (var i = 1; i < existing.length; i++) {
      if (String(existing[i][1]) === dateAz) return; // already captured for this day
    }

    var url = 'https://api.open-meteo.com/v1/forecast'
      + '?latitude=' + coords.lat + '&longitude=' + coords.lon
      + '&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,wind_speed_10m,uv_index'
      + '&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=America%2FPhoenix';
    var resp = UrlFetchApp.fetch(url, {muteHttpExceptions: true});
    if (resp.getResponseCode() !== 200) {
      console.error('Open-Meteo request failed: HTTP ' + resp.getResponseCode());
      return;
    }

    var body = JSON.parse(resp.getContentText());
    var hourly = body.hourly;
    if (!hourly || !hourly.time || hourly.time.length === 0) return;

    // hourly.time values are local wall-clock strings (e.g. "2026-07-24T09:00")
    // in the requested timezone -- Arizona has no DST, so a fixed -07:00
    // offset always parses them correctly as real instants for comparison.
    var targetMs = new Date(tsISO).getTime();
    var idx = 0, bestDiff = Infinity;
    for (var h = 0; h < hourly.time.length; h++) {
      var diff = Math.abs(new Date(hourly.time[h] + ':00-07:00').getTime() - targetMs);
      if (diff < bestDiff) { bestDiff = diff; idx = h; }
    }

    forecastSheet.appendRow([
      tsISO, dateAz, body.latitude, body.longitude,
      hourly.temperature_2m[idx],
      hourly.precipitation_probability[idx],
      hourly.wind_speed_10m[idx],
      hourly.relative_humidity_2m[idx],
      hourly.uv_index[idx],
      'open-meteo'
    ]);
  } catch (err) {
    // Never let a forecast-capture failure break observation logging.
    console.error('Forecast capture failed: ' + err.toString());
  }
}

// ---------------------------------------------------------------------------
// _exportSheet — read-only export of any sheet as JSON, optionally date-filtered
// ---------------------------------------------------------------------------
// Used by action=export. Generic across "Environmental Data", "Hiking Observations",
// "GPS Track", and "Hike Start Forecast" — all four have a real ISO 8601 timestamp
// in column A, which this filters on. ("Timeline" also works but its column A is an
// Arizona-local display string, not UTC ISO — start/end filtering on it is not
// reliable; fetch it unfiltered and filter client-side if needed.)
//
// Params: sheet=<name> (required), start=<ISO ts> (optional), end=<ISO ts> (optional)
// Returns: {status:'ok', sheet, count, rows: [{header: value, ...}, ...]}

function _exportSheet(sheetName, startParam, endParam) {
  if (!sheetName) {
    return ContentService
      .createTextOutput(JSON.stringify({status: 'error', message: 'missing sheet parameter'}))
      .setMimeType(ContentService.MimeType.JSON);
  }

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) {
    return ContentService
      .createTextOutput(JSON.stringify({status: 'error', message: 'unknown sheet: ' + sheetName}))
      .setMimeType(ContentService.MimeType.JSON);
  }

  var data = sheet.getDataRange().getValues();
  if (data.length === 0) {
    return ContentService
      .createTextOutput(JSON.stringify({status: 'ok', sheet: sheetName, count: 0, rows: []}))
      .setMimeType(ContentService.MimeType.JSON);
  }

  var headers   = data[0];
  var startTime = startParam ? new Date(startParam).getTime() : -Infinity;
  var endTime   = endParam ? new Date(endParam).getTime() : Infinity;

  var rows = [];
  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    var tsRaw = row[0];
    if (!tsRaw) continue;
    var tsDate = new Date(tsRaw);
    if (isNaN(tsDate.getTime())) continue;
    var t = tsDate.getTime();
    if (t < startTime || t > endTime) continue;

    var obj = {};
    for (var c = 0; c < headers.length; c++) {
      var val = row[c];
      if (val instanceof Date) val = val.toISOString();
      obj[headers[c]] = val;
    }
    rows.push(obj);
  }

  return ContentService
    .createTextOutput(JSON.stringify({status: 'ok', sheet: sheetName, count: rows.length, rows: rows}))
    .setMimeType(ContentService.MimeType.JSON);
}

// ---------------------------------------------------------------------------
// doGet — GPS track write and lookup (GPSLogger + Node-RED → GPS Track sheet)
// ---------------------------------------------------------------------------
// action=gps    GPSLogger posts a trackpoint every 30 seconds while hiking.
//               Appends one row to "GPS Track" sheet.
//
// action=lookup Node-RED calls this for each sensor reading during upload.
//               Returns lat/lon of the nearest GPS trackpoint within ±5 minutes,
//               or {lat:null, lon:null} if no match.
//
// action=export Read-only export of a whole sheet as JSON, optionally filtered by
//               an ISO 8601 [start, end] timestamp range on column A. See _exportSheet.
//               Example: ?action=export&sheet=Environmental%20Data&start=2026-06-15T00:00:00Z&end=2026-06-29T23:59:59Z
//
// action=version Returns {status:'ok', version: SCRIPT_VERSION} — no other side effects.
//                Cheapest way to confirm a redeploy actually took effect.

function doGet(e) {
  try {
    var expectedKey = PropertiesService.getScriptProperties().getProperty('API_KEY');
    if (!expectedKey || e.parameter.key !== expectedKey) {
      return ContentService
        .createTextOutput(JSON.stringify({status: 'error', message: 'unauthorized'}))
        .setMimeType(ContentService.MimeType.JSON);
    }

    var action = e.parameter.action;

    if (action === 'gps') {
      var lat     = parseFloat(e.parameter.lat);
      var lon     = parseFloat(e.parameter.lon);
      var acc     = parseFloat(e.parameter.acc);
      var alt     = parseFloat(e.parameter.alt);
      // %TIME from GPSLogger may be a Unix epoch integer (seconds or ms) or an
      // ISO date string depending on app version. Parse robustly:
      var tsRaw = e.parameter.ts;
      var tsDate;
      if (/^\d+$/.test(tsRaw)) {
        var n = Number(tsRaw);
        tsDate = new Date(n.toString().length >= 13 ? n : n * 1000);
      } else {
        tsDate = new Date(tsRaw);
      }
      var tsISO = tsDate.toISOString();

      var ss = SpreadsheetApp.getActiveSpreadsheet();
      var gpsSheet = ss.getSheetByName('GPS Track');
      gpsSheet.appendRow([tsISO, lat, lon, acc, alt]);

      return ContentService
        .createTextOutput(JSON.stringify({status: 'ok'}))
        .setMimeType(ContentService.MimeType.JSON);

    } else if (action === 'lookup') {
      var ts = e.parameter.ts;
      var ss = SpreadsheetApp.getActiveSpreadsheet();
      var coords = _gpsLookup(ss, ts);
      return ContentService
        .createTextOutput(JSON.stringify(coords))
        .setMimeType(ContentService.MimeType.JSON);

    } else if (action === 'export') {
      return _exportSheet(e.parameter.sheet, e.parameter.start, e.parameter.end);

    } else if (action === 'version') {
      return ContentService
        .createTextOutput(JSON.stringify({status: 'ok', version: SCRIPT_VERSION}))
        .setMimeType(ContentService.MimeType.JSON);

    } else {
      return ContentService
        .createTextOutput(JSON.stringify({status: 'error', message: 'unknown action', version: SCRIPT_VERSION}))
        .setMimeType(ContentService.MimeType.JSON);
    }

  } catch(err) {
    return ContentService
      .createTextOutput(JSON.stringify({status: 'error', message: err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
