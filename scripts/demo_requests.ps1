param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

function Invoke-JsonPost {
    param(
        [string]$Path,
        [hashtable]$Body
    )

    $json = $Body | ConvertTo-Json -Depth 8
    Invoke-RestMethod -Method Post -Uri "$BaseUrl$Path" -ContentType "application/json" -Body $json
}

Write-Host "Health"
$health = Invoke-RestMethod -Uri "$BaseUrl/health"
$health | ConvertTo-Json -Depth 8

Write-Host "`nMulti-step chat"
$multiStep = Invoke-JsonPost -Path "/chat" -Body @{
    user_id = "U_STUDENT_001"
    student_id = "S001"
    message = "Show my attendance, Mathematics marks, and pending fees."
    return_plan = $true
}
$multiStep | ConvertTo-Json -Depth 12

Write-Host "`nFollow-up using conversation memory"
$followUp = Invoke-JsonPost -Path "/chat" -Body @{
    user_id = "U_STUDENT_001"
    student_id = "S001"
    conversation_id = $multiStep.conversation_id
    message = "Which one is highest?"
    return_plan = $true
}
$followUp | ConvertTo-Json -Depth 12

Write-Host "`nExecution logs"
$logs = Invoke-RestMethod -Uri "$BaseUrl/logs?conversation_id=$($multiStep.conversation_id)"
$logs | ConvertTo-Json -Depth 12
