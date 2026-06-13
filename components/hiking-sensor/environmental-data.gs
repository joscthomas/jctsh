// Google Apps Script — JCTsh Environmental Data
// Spreadsheet: "JCTsh Environmental Data"
// Repo: components/hiking-sensor/environmental-data.gs
//
// To deploy: paste this entire file into the Apps Script editor (Extensions → Apps Script),
// then Deploy → Manage deployments → pencil → Version: New version → Save.
// The deployment URL does not change on redeployment.
//
// API_KEY is stored in Script Properties (Project Settings → Script Properties).
// The same key is stored in Node-RED environment variables and credentials.local.md.

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

      // Strip "observation" keyword prefix — tolerates punctuation/spaces after keyword
      var obsText = (payload.observation || '').trim();
      obsText = obsText.replace(/^selah[:\s,]*/i, '').trim();

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

      obsSheet.appendRow([ts, obsText, JSON.stringify(categories), payload.source || 'voice']);

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
        v('voc_index'),       // W
        v('nox_index')        // X
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
// doGet — GPS track write and lookup (GPSLogger + Node-RED → GPS Track sheet)
// ---------------------------------------------------------------------------
// action=gps    GPSLogger posts a trackpoint every 30 seconds while hiking.
//               Appends one row to "GPS Track" sheet.
//
// action=lookup Node-RED calls this for each sensor reading during upload.
//               Returns lat/lon of the nearest GPS trackpoint within ±5 minutes,
//               or {lat:null, lon:null} if no match.

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
      var ts         = e.parameter.ts;
      var targetTime = new Date(ts).getTime();
      var fiveMin    = 5 * 60 * 1000;

      var ss = SpreadsheetApp.getActiveSpreadsheet();
      var gpsSheet = ss.getSheetByName('GPS Track');
      var data = gpsSheet.getDataRange().getValues();

      // data[0] is the header row
      if (data.length <= 1) {
        return ContentService
          .createTextOutput(JSON.stringify({lat: null, lon: null}))
          .setMimeType(ContentService.MimeType.JSON);
      }

      var bestRow  = null;
      var bestDiff = Infinity;

      for (var i = 1; i < data.length; i++) {
        var rowTime = new Date(data[i][0]).getTime();
        var diff    = Math.abs(targetTime - rowTime);
        if (diff < bestDiff) {
          bestDiff = diff;
          bestRow  = data[i];
        }
      }

      if (bestDiff <= fiveMin && bestRow !== null) {
        return ContentService
          .createTextOutput(JSON.stringify({lat: bestRow[1], lon: bestRow[2]}))
          .setMimeType(ContentService.MimeType.JSON);
      } else {
        return ContentService
          .createTextOutput(JSON.stringify({lat: null, lon: null}))
          .setMimeType(ContentService.MimeType.JSON);
      }

    } else {
      return ContentService
        .createTextOutput(JSON.stringify({status: 'error', message: 'unknown action'}))
        .setMimeType(ContentService.MimeType.JSON);
    }

  } catch(err) {
    return ContentService
      .createTextOutput(JSON.stringify({status: 'error', message: err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
