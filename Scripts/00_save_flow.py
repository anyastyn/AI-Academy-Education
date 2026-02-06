import os, json, requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
USER_ID = os.getenv("USER_ID")

print("SUPABASE_URL:", SUPABASE_URL)
print("USER_ID:", USER_ID)

# ✅ Paste your FULL JSON between the triple quotes
FLOW_JSON = r'''
{"name":"714031cb-364a-492f-9f0b-6650fbbfb6a5","id":"/providers/Microsoft.Flow/flows/714031cb-364a-492f-9f0b-6650fbbfb6a5","type":"Microsoft.Flow/flows","properties":{"apiId":"/providers/Microsoft.PowerApps/apis/shared_logicflows","displayName":"Backup 5 weeks VEEAM Email Attachments to SharePoint","definition":{"metadata":{"workflowEntityId":null,"processAdvisorMetadata":null,"flowChargedByPaygo":null,"flowclientsuspensionreason":"None","flowclientsuspensiontime":null,"flowclientsuspensionreasondetails":null,"creator":{"id":"f2637cd9-61a8-44a4-be81-d1def1fe5a6f","type":"User","tenantId":"f260df36-bc43-424c-8f44-c85226657b01"},"provisioningMethod":"FromDefinition","failureAlertSubscription":true,"clientLastModifiedTime":"2025-08-21T11:43:11.3052661Z","connectionKeySavedTimeKey":"2025-12-11T11:40:01.8277158Z","creationSource":null,"modifiedSources":"Portal"},"$schema":"https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#","contentVersion":"1.0.0.0","parameters":{"$connections":{"defaultValue":{},"type":"Object"},"$authentication":{"defaultValue":{},"type":"SecureObject"}},"triggers":{"When_a_new_email_arrives_(V3)":{"splitOn":"@triggerOutputs()?['body/value']","metadata":{"operationMetadataId":"7aafa9d7-8795-416a-940d-3a4105e06265"},"type":"OpenApiConnectionNotification","inputs":{"host":{"apiId":"/providers/Microsoft.PowerApps/apis/shared_office365","connectionName":"shared_office365","operationId":"OnNewEmailV3"},"parameters":{"folderPath":"Inbox","to":"anna.Styn@kyndryl.com","from":"seint3618@sandvik.com","includeAttachments":true,"subjectFilter":"[EXTERNAL] Report Veeam 5 week Backup report - Power BI","importance":"Any","fetchOnlyWithAttachment":true},"authentication":"@parameters('$authentication')"}}},"actions":{"Apply_to_each":{"foreach":"@triggerOutputs()?['body/attachments']","actions":{"Get_Attachment_(V2)":{"runAfter":{},"metadata":{"operationMetadataId":"d53b7a5c-47f8-4de4-a92c-58f846759678"},"type":"OpenApiConnection","inputs":{"host":{"apiId":"/providers/Microsoft.PowerApps/apis/shared_office365","connectionName":"shared_office365","operationId":"GetAttachment_V2"},"parameters":{"messageId":"@triggerOutputs()?['body/id']","attachmentId":"@items('Apply_to_each')?['id']","extractSensitivityLabel":"false","fetchSensitivityLabelMetadata":"false"},"authentication":"@parameters('$authentication')"}},"Create_file":{"runAfter":{"Get_Attachment_(V2)":["Succeeded"]},"metadata":{"operationMetadataId":"e027d6a9-e6b6-4f2d-b1a7-219ae4cd9f76"},"type":"OpenApiConnection","inputs":{"host":{"apiId":"/providers/Microsoft.PowerApps/apis/shared_sharepointonline","connectionName":"shared_sharepointonline_1","operationId":"CreateFile"},"parameters":{"dataset":"https://kyndryl.sharepoint.com/sites/WoodServiceLevelManagementReporting","folderPath":"/Shared Documents/Sandvik Backup Source Files","name":"@outputs('Get_Attachment_(V2)')?['body/name']","body":"@outputs('Get_Attachment_(V2)')?['body/contentBytes']"},"authentication":"@parameters('$authentication')"},"runtimeConfiguration":{"contentTransfer":{"transferMode":"Chunked"}}}},"runAfter":{},"metadata":{"operationMetadataId":"8768b9a7-4c6a-4772-a83f-d52cbf17017d"},"type":"Foreach"}}},"connectionReferences":{"shared_office365":{"connectionName":"shared-office365-dfc0ba70-e998-419e-91ba-afae4781d8a7","source":"Embedded","id":"/providers/Microsoft.PowerApps/apis/shared_office365","tier":"NotSpecified","apiName":"office365","isProcessSimpleApiReferenceConversionAlreadyDone":false},"shared_sharepointonline_1":{"connectionName":"f3f9737c5bc34316a72dfeeaf4112f88","source":"Embedded","id":"/providers/Microsoft.PowerApps/apis/shared_sharepointonline","tier":"NotSpecified","apiName":"sharepointonline","isProcessSimpleApiReferenceConversionAlreadyDone":false}},"flowFailureAlertSubscribed":false,"isManaged":false}}
'''

# 1) Parse JSON (if this fails, JSON is incomplete)
flow = json.loads(FLOW_JSON)

name = flow["properties"]["displayName"]
triggers = list(flow["properties"]["definition"]["triggers"].keys())
actions = list(flow["properties"]["definition"]["actions"].keys())

summary = (
    f"Flow: {name}\n"
    f"Triggers: {triggers}\n"
    f"Top-level actions: {actions}\n"
    f"Purpose: Save email attachments to SharePoint.\n"
)

content = (
    "FLOW EXPORT (JSON) + SUMMARY\n\n"
    + summary
    + "\n---\nFULL JSON:\n"
    + FLOW_JSON
)

payload = [{
    "user_id": USER_ID,
    "role": "user",
    "content": content,
    "metadata": {
        "type": "power_automate_flow_export",
        "flow_display_name": name,
        "triggers": triggers,
        "actions": actions
    }
}]

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

url = f"{SUPABASE_URL}/rest/v1/messages"
resp = requests.post(url, headers=headers, json=payload, timeout=60)

print("Status:", resp.status_code)
print(resp.text)

resp.raise_for_status()
data = resp.json()
print("✅ Inserted message id:", data[0]["id"])


