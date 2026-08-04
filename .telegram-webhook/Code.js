function doPost(e) {
  if (!e || !e.postData || !e.postData.contents) {
    return ContentService.createTextOutput("No data");
  }

  var contents = e.postData.contents;
  var payloadJson;
  try {
    payloadJson = JSON.parse(contents);
  } catch(err) {
    return ContentService.createTextOutput("OK");
  }

  // Research digest has its own fast synchronous path
  if (payloadJson.action === "research_digest") {
    return handleResearchDigest(payloadJson);
  }

  var updateId = payloadJson.update_id;

  // Idempotency: instantly reject duplicates before doing anything slow
  var cache = CacheService.getScriptCache();
  if (updateId && cache.get(updateId.toString())) {
    return ContentService.createTextOutput("OK");
  }

  // Store payload FIRST so it's safe before we attempt dispatch
  var props = PropertiesService.getScriptProperties();
  var key = "pending_" + (updateId || Date.now().toString());
  props.setProperty(key, contents);

  // Mark as seen AFTER storing — prevents losing it if GitHub call is slow
  if (updateId) {
    cache.put(updateId.toString(), "1", 300);
  }

  // Attempt synchronous dispatch with a short deadline so Telegram
  // always gets its 200 back well within the 5-second window.
  var dispatched = dispatchToGitHub(payloadJson, props, key);

  if (!dispatched) {
    // Dispatch failed/timed out — payload is already in Properties.
    // Schedule a background retry so it's processed in ~1 min.
    ScriptApp.newTrigger("dispatchPendingToGitHub")
      .timeBased()
      .after(60000)
      .create();
  }

  return ContentService.createTextOutput("OK");
}

// Attempts a single GitHub repository_dispatch. Returns true on HTTP 204.
function dispatchToGitHub(payloadJson, props, key) {
  var GITHUB_PAT = props.getProperty("GITHUB_PAT");
  var options = {
    "method": "post",
    "headers": {
      "Authorization": "Bearer " + GITHUB_PAT,
      "Accept": "application/vnd.github.v3+json"
    },
    "contentType": "application/json",
    "payload": JSON.stringify({
      "event_type": "telegram_webhook",
      "client_payload": payloadJson
    }),
    "muteHttpExceptions": true
  };

  try {
    var resp = UrlFetchApp.fetch(
      "https://api.github.com/repos/Vedant2100/ai-weekly-reads/dispatches",
      options
    );
    var code = resp.getResponseCode();
    console.log("GitHub dispatch HTTP " + code);
    if (code === 204) {
      props.deleteProperty(key); // clean up — successfully dispatched
      return true;
    }
    console.error("GitHub dispatch non-204: " + resp.getContentText());
    return false;
  } catch(err) {
    console.error("GitHub dispatch exception: " + err);
    return false;
  }
}

// Background retry: processes any payloads left in Properties by a failed dispatch.
function dispatchPendingToGitHub() {
  // Clean up this trigger so they don't accumulate
  ScriptApp.getProjectTriggers().forEach(function(t) {
    if (t.getHandlerFunction() === "dispatchPendingToGitHub") {
      ScriptApp.deleteTrigger(t);
    }
  });

  var props = PropertiesService.getScriptProperties();
  var all = props.getProperties();

  Object.keys(all).forEach(function(key) {
    if (!key.startsWith("pending_")) return;
    var contents = all[key];
    var payloadJson;
    try { payloadJson = JSON.parse(contents); } catch(e) { props.deleteProperty(key); return; }
    props.deleteProperty(key);
    dispatchToGitHub(payloadJson, props, key);
  });
}


function handleResearchDigest(payload) {
  var properties = PropertiesService.getScriptProperties();
  var expectedSecret = properties.getProperty("RESEARCH_DIGEST_SECRET") || properties.getProperty("GITHUB_PAT");
  if (!expectedSecret || payload.secret !== expectedSecret) {
    return jsonResponse({ok: false, error: "unauthorized"});
  }

  var recipient = properties.getProperty("RESEARCH_EMAIL_TO")
    || Session.getEffectiveUser().getEmail()
    || Session.getActiveUser().getEmail();
  if (!recipient) {
    return jsonResponse({ok: false, error: "no recipient configured"});
  }

  try {
    appendResearchRows(payload.rows || [], properties);
    MailApp.sendEmail({
      to: recipient,
      subject: payload.subject || "AI Research Reorientation",
      body: payload.body || "",
      htmlBody: payload.html_body || payload.body || ""
    });
    return jsonResponse({ok: true, recipient: recipient});
  } catch (error) {
    console.error("Research digest delivery failed: " + error);
    return jsonResponse({ok: false, error: String(error)});
  }
}

function appendResearchRows(rows, properties) {
  var spreadsheetId = properties.getProperty("RESEARCH_SHEET_ID");
  var spreadsheet = spreadsheetId
    ? SpreadsheetApp.openById(spreadsheetId)
    : SpreadsheetApp.create(properties.getProperty("RESEARCH_SHEET_TITLE") || "AI Research Link Library");
  if (!spreadsheetId) {
    properties.setProperty("RESEARCH_SHEET_ID", spreadsheet.getId());
  }

  var sheetName = properties.getProperty("RESEARCH_SHEET_NAME") || "Links";
  var sheet = spreadsheet.getSheetByName(sheetName) || spreadsheet.insertSheet(sheetName);
  if (sheet.getLastRow() === 0) {
    sheet.appendRow([
      "captured_at",
      "processed_at",
      "type",
      "title",
      "url",
      "source",
      "published",
      "transcript_method",
      "summary_status",
      "digest_date"
    ]);
  }

  rows.forEach(function(row) {
    sheet.appendRow([
      row.captured_at || "",
      row.processed_at || "",
      row.type || "",
      row.title || "",
      row.url || "",
      row.source || "",
      row.published || "",
      row.transcript_method || "",
      row.summary_status || "",
      row.digest_date || ""
    ]);
  });
}

function jsonResponse(value) {
  return ContentService
    .createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}

// Run this once from the Apps Script editor to grant the new Mail and Sheets scopes.
// The web app then runs with the same deploying account and can deliver automatically.
function authorizeResearchDelivery() {
  var properties = PropertiesService.getScriptProperties();
  var recipient = properties.getProperty("RESEARCH_EMAIL_TO")
    || Session.getEffectiveUser().getEmail()
    || Session.getActiveUser().getEmail();
  MailApp.getRemainingDailyQuota();
  var spreadsheetId = properties.getProperty("RESEARCH_SHEET_ID");
  if (spreadsheetId) {
    SpreadsheetApp.openById(spreadsheetId).getName();
  } else {
    var spreadsheet = SpreadsheetApp.create(properties.getProperty("RESEARCH_SHEET_TITLE") || "AI Research Link Library");
    properties.setProperty("RESEARCH_SHEET_ID", spreadsheet.getId());
  }
  return recipient || "No recipient found; set RESEARCH_EMAIL_TO in Script properties.";
}
