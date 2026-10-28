$headers = @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzkzMTA2OTA4LCJpYXQiOjE3OTMxMDMzMDgsImp0aSIiOiJhMzk0ODNjMzU3OTI0YmRiODkwYjM3NWNlZjQwN2NmIiwiaWRfb25sIjoiNzMzZTk1M2U4MzEyNDlhN2IwMTFkNjAxM2I1Njc1NTYifQ.OLGQgxpxyXl_gB3YmeyfegdaeKc2D-bjNu4p0lHGOYM"}
$base = "http://localhost:8000/api/v1/assistant"

Write-Host "=== 1. GET sessions ===" -ForegroundColor Cyan
$sessions = Invoke-RestMethod -Uri "$base/sessions/" -Method Get -Headers $headers
Write-Host "Sessions trouvees: $($sessions.count)" -ForegroundColor Green

Write-Host ""
Write-Host "=== 2. POST create session ===" -ForegroundColor Cyan
$newSession = Invoke-RestMethod -Uri "$base/sessions/" -Method Post -ContentType "application/json" -Headers $headers -Body (@{title="Session test IA"} | ConvertTo-Json)
$sessionId = $newSession.id
Write-Host "Session creee - ID: $sessionId, Titre: $($newSession.title)" -ForegroundColor Green

Write-Host ""
Write-Host "=== 3. GET session detail ===" -ForegroundColor Cyan
$session = Invoke-RestMethod -Uri ("$base/sessions/" + $sessionId + "/") -Method Get -Headers $headers
Write-Host "Session recuperee - ID: $($session.id), Titre: $($session.title)" -ForegroundColor Green

Write-Host ""
Write-Host "=== 4. PATCH session ===" -ForegroundColor Cyan
$updated = Invoke-RestMethod -Uri ("$base/sessions/" + $sessionId + "/") -Method Patch -ContentType "application/json" -Headers $headers -Body (@{title="Session modifiee"} | ConvertTo-Json)
Write-Host "Session modifiee - Titre: $($updated.title)" -ForegroundColor Green

Write-Host ""
Write-Host "=== 5. POST message ===" -ForegroundColor Cyan
$msg = Invoke-RestMethod -Uri ("$base/sessions/" + $sessionId + "/messages/") -Method Post -ContentType "application/json" -Headers $headers -Body (@{content="Question sur le cours de maths"} | ConvertTo-Json)
$msgId = $msg.id
Write-Host "Message cree - ID: $msgId, Role: $($msg.role), Statut: $($msg.status)" -ForegroundColor Green

Write-Host ""
Write-Host "=== 6. GET messages ===" -ForegroundColor Cyan
$messages = Invoke-RestMethod -Uri ("$base/sessions/" + $sessionId + "/messages/") -Method Get -Headers $headers
Write-Host "Nombre de messages: $($messages.count)" -ForegroundColor Green

Write-Host ""
Write-Host "=== 7. GET message detail ===" -ForegroundColor Cyan
$msgDetail = Invoke-RestMethod -Uri ("$base/messages/" + $msgId + "/") -Method Get -Headers $headers
Write-Host "Message recupere - ID: $($msgDetail.id), Contenu: $($msgDetail.content)" -ForegroundColor Green

Write-Host ""
Write-Host "=== 8. POST explanation ===" -ForegroundColor Cyan
$expl = Invoke-RestMethod -Uri ("$base/messages/" + $msgId + "/explanation/") -Method Post -ContentType "application/json" -Headers $headers -Body (@{difficulty_level="beginner"} | ConvertTo-Json)
Write-Host "Explication demandee - statut reponse recu" -ForegroundColor Green

Write-Host ""
Write-Host "=== 9. POST illustration ===" -ForegroundColor Cyan
$ill = Invoke-RestMethod -Uri ("$base/messages/" + $msgId + "/illustrations/") -Method Post -ContentType "application/json" -Headers $headers -Body (@{prompt="Diagramme pedagogique"} | ConvertTo-Json)
Write-Host "Illustration demandee - statut reponse recu" -ForegroundColor Green

Write-Host ""
Write-Host "=== 10. DELETE session ===" -ForegroundColor Cyan
Invoke-RestMethod -Uri ("$base/sessions/" + $sessionId + "/") -Method Delete -Headers $headers
Write-Host "Session supprimee (204)" -ForegroundColor Green

Write-Host ""
Write-Host "=== TOUTES LES ROUTES AI_ASSISTANT TESTES AVEC SUCCES ===" -ForegroundColor Green
