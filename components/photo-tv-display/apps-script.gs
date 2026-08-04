// Google Apps Script — photo-tv-display Deletion Log
// Spreadsheet: a new, dedicated Sheet (NOT the JCTsh Environmental Data sheet --
// kept isolated per Phase 2 planning, no shared Apps Script logic between the
// two components).
// Repo: components/photo-tv-display/apps-script.gs
//
// To deploy:
// 1. Create a new Google Sheet, e.g. "JCTsh Photo Deletion Log".
// 2. Add a sheet tab named "Deletions" with header row:
//    timestamp | filename | date_taken | album_folder | immich_asset_id | deleted_by
// 3. Extensions -> Apps Script, paste this entire file in, replacing the default code.
// 4. Project Settings -> Script Properties -> add API_KEY with the value from
//    DELETION_LOG_SHEET_APPS_SCRIPT_KEY in components/photo-tv-display/.env.
// 5. Deploy -> New deployment -> Web app -> Execute as: Me, Who has access: Anyone.
// 6. Copy the deployment URL into DELETION_LOG_SHEET_APPS_SCRIPT_URL in
//    components/photo-tv-display/.env on the M8, restart the photo-tv-display
//    service.
// 7. On future edits: Deploy -> Manage deployments -> pencil -> Version: New
//    version -> Save. The deployment URL does not change on redeploy.
//
// SCRIPT_VERSION exists purely to make it easy to confirm a redeploy actually
// took effect, same convention as environmental-data.gs.

var SCRIPT_VERSION = '2026-08-03.1-initial';

function doPost(e) {
  try {
    var expectedKey = PropertiesService.getScriptProperties().getProperty('API_KEY');
    if (!expectedKey || e.parameter.key !== expectedKey) {
      return ContentService
        .createTextOutput(JSON.stringify({status: 'error', message: 'unauthorized'}))
        .setMimeType(ContentService.MimeType.JSON);
    }

    var record = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName('Deletions');

    sheet.appendRow([
      record.timestamp,
      record.filename,
      record.date_taken,
      record.album_folder,
      record.immich_asset_id,
      record.deleted_by
    ]);

    return ContentService
      .createTextOutput(JSON.stringify({status: 'ok', version: SCRIPT_VERSION}))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({status: 'error', message: err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// Cheapest way to confirm a redeploy actually took effect -- GET the
// deployment URL with ?action=version (no key required, no side effects).
function doGet(e) {
  return ContentService
    .createTextOutput(JSON.stringify({status: 'ok', version: SCRIPT_VERSION}))
    .setMimeType(ContentService.MimeType.JSON);
}
