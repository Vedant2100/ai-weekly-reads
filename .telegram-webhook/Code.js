function doPost(e) {
  var GITHUB_PAT = PropertiesService.getScriptProperties().getProperty("GITHUB_PAT");

  if (!e || !e.postData || !e.postData.contents) {
    return ContentService.createTextOutput("No data");
  }

  var contents = e.postData.contents;
  var payloadJson = JSON.parse(contents);
  if (payloadJson.action === "research_digest") {
    return handleResearchDigest(payloadJson);
  }
  var updateId = payloadJson.update_id;

  var cache = CacheService.getScriptCache();
  if (updateId && cache.get(updateId.toString())) {
    return ContentService.createTextOutput("OK");
  }

  if (updateId) {
    cache.put(updateId.toString(), "processed", 300); // lock for 5 minutes
  }

  var url = "https://api.github.com/repos/Vedant2100/ai-weekly-reads/dispatches";

  var payload = {
    "event_type": "telegram_webhook",
    "client_payload": payloadJson
  };

  var options = {
    "method": "post",
    "headers": {
      "Authorization": "Bearer " + GITHUB_PAT,
      "Accept": "application/vnd.github.v3+json"
    },
    "contentType": "application/json",
    "payload": JSON.stringify(payload)
  };

  try {
    UrlFetchApp.fetch(url, options);
  } catch(error) {
    console.error("Error calling GitHub:", error);
  }

  return ContentService.createTextOutput("OK");
}

// Temporary, token-gated end-to-end probe. Removed after verification.
var CODEX_E2E_TOKEN_SHA256 = "6c7ed13615cd96ea2e2d5cf4b6a2982702e76ea67c036c6dc83f96d0ba6bc0ec";

function doGet(e) {
  if (!codexE2EAuthorized_(e && e.parameter && e.parameter.token)) {
    return jsonResponse({ok: false, error: "unauthorized"});
  }

  var properties = PropertiesService.getScriptProperties();
  var secret = properties.getProperty("RESEARCH_DIGEST_SECRET")
    || properties.getProperty("GITHUB_PAT");
  var now = new Date().toISOString();

  return handleResearchDigest({
    action: "research_digest",
    secret: secret,
    subject: "AI Weekly Reads end-to-end test",
    body: "The live AI Weekly email and Google Sheets delivery path completed successfully.",
    html_body: "<p><strong>AI Weekly Reads end-to-end test passed.</strong></p><p>The live email and Google Sheets delivery path completed successfully.</p>",
    rows: [{
      captured_at: now,
      processed_at: now,
      type: "link",
      title: "Codex end-to-end delivery test",
      url: "https://example.com/codex-e2e-test",
      source: "codex-e2e",
      summary_status: "e2e_test",
      digest_date: now.substring(0, 10)
    }]
  });
}

function codexE2EAuthorized_(token) {
  var digest = Utilities.computeDigest(
    Utilities.DigestAlgorithm.SHA_256,
    String(token || ""),
    Utilities.Charset.UTF_8
  );
  var hex = digest.map(function(byte) {
    var value = byte < 0 ? byte + 256 : byte;
    return ("0" + value.toString(16)).slice(-2);
  }).join("");
  return hex === CODEX_E2E_TOKEN_SHA256;
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
