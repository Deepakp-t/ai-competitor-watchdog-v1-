# Script to create GitHub repository using GitHub API
# Usage: .\create_repo.ps1 -Token "your_github_token"

param(
    [Parameter(Mandatory=$true)]
    [string]$Token,
    
    [string]$RepoName = "ai-competitor-watchdog-v1-",
    [string]$Owner = "Deepakp-t",
    [string]$Description = "AI-powered competitor monitoring system for contract management & e-signature space",
    [switch]$Private = $false
)

$headers = @{
    "Authorization" = "token $Token"
    "Accept" = "application/vnd.github.v3+json"
}

$body = @{
    name = $RepoName
    description = $Description
    private = $Private
    auto_init = $false
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $headers -Body $body -ContentType "application/json"
    
    Write-Host "Repository created successfully!" -ForegroundColor Green
    Write-Host "Repository URL: $($response.html_url)" -ForegroundColor Cyan
    Write-Host "Clone URL: $($response.clone_url)" -ForegroundColor Cyan
    
    return $response
} catch {
    Write-Host "Error creating repository: $_" -ForegroundColor Red
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "Authentication failed. Please check your token." -ForegroundColor Yellow
    } elseif ($_.Exception.Response.StatusCode -eq 422) {
        Write-Host "Repository may already exist or name is invalid." -ForegroundColor Yellow
    }
    throw
}
