function doPost(e) {
  var GITHUB_PAT = PropertiesService.getScriptProperties().getProperty("GITHUB_PAT");

  if (!e || !e.postData || !e.postData.contents) {
    return ContentService.createTextOutput("No data");
  }

  var contents = e.postData.contents;
  var payloadJson = JSON.parse(contents);
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
