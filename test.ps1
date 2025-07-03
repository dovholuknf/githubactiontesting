# test-bool.ps1
param (
  [bool]$Flag = $false
)

if ($Flag) {
  Write-Output "✅ Flag is TRUE"
} else {
  Write-Output "❌ Flag is FALSE"
}