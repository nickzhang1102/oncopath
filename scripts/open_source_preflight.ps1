param(
    [string]$Root = (Get-Location).Path
)

$ErrorActionPreference = "Stop"

function Add-Finding {
    param(
        [System.Collections.Generic.List[object]]$Findings,
        [string]$Severity,
        [string]$Category,
        [string]$Path,
        [string]$Detail
    )

    $Findings.Add([pscustomobject]@{
        Severity = $Severity
        Category = $Category
        Path = $Path
        Detail = $Detail
    }) | Out-Null
}

function Test-GitPublicCandidate {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath (Join-Path $Root $Path))) {
        return $false
    }

    git -C $Root check-ignore -q -- $Path 2>$null
    return $LASTEXITCODE -ne 0
}

if (-not (Test-Path -LiteralPath $Root)) {
    throw "Root path does not exist: $Root"
}

$findings = [System.Collections.Generic.List[object]]::new()

$publicFiles = @(
    git -C $Root ls-files --cached --others --exclude-standard |
        Sort-Object -Unique
)

$sensitivePatterns = @(
    @{ Name = "quoted credential-shaped assignment"; Pattern = '(?i)(SECRET_KEY|API_KEY|ENCRYPTION_KEY|INTEGRATION_SECRET)\s*[:=]\s*([''"])[A-Za-z0-9+/=_-]{16,}\2' },
    @{ Name = "environment credential-shaped assignment"; Pattern = '(?i)^(SECRET_KEY|[A-Z_]*API_KEY|ENCRYPTION_KEY|INTEGRATION_SECRET)=[A-Za-z0-9+/=_-]{16,}' },
    @{ Name = "OpenAI-style secret"; Pattern = "sk-[A-Za-z0-9_-]{16,}" },
    @{ Name = "JWT-shaped token"; Pattern = "eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}" },
    @{ Name = "private key material"; Pattern = "-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----" },
    @{ Name = "private-network address"; Pattern = "(?<!\d)(10\.(?:\d{1,3}\.){2}\d{1,3}|192\.168\.(?:\d{1,3}\.)\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.(?:\d{1,3}\.)\d{1,3})(?!\d)" },
    @{ Name = "local absolute path"; Pattern = "(?i)(?:[A-Z]:[\\/](?:Users|dev)[\\/]|/Users/[A-Za-z0-9._-]+/)" },
    @{ Name = "Chinese mobile number"; Pattern = "(?<!\d)1[3-9]\d{9}(?!\d)" },
    @{ Name = "Chinese identity number"; Pattern = "(?<!\d)\d{17}[0-9Xx](?!\d)" }
)

$knownPublicExamples = @(
    "your-super-secret-key-change-this-in-production-must-be-at-least-32-chars",
    "your-secret-key-change-in-production",
    "your-llm-api-key",
    "your-ocr-api-key",
    "YourStr0ngDBPassword!",
    "YourStr0ngRedisPassword!"
)

$knownSyntheticExamples = @(
    "13800138000",
    "13900139000",
    "13900139999",
    "13812345678",
    "13987654321",
    "110101199001011234",
    "110101199001150011",
    "110101198505150011"
)

$syntheticExamplePaths = @(
    "back/app/services/desensitization.py",
    "back/scripts/create_test_data.py",
    "scripts/open_source_preflight.ps1"
)

foreach ($file in $publicFiles) {
    $fullPath = Join-Path $Root $file
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        continue
    }

    foreach ($rule in $sensitivePatterns) {
        try {
            $matches = Select-String -LiteralPath $fullPath -Pattern $rule.Pattern -AllMatches -ErrorAction Stop
            foreach ($match in $matches) {
                $isKnownExample = $false
                foreach ($example in $knownPublicExamples) {
                    if ($match.Line.Contains($example)) {
                        $isKnownExample = $true
                        break
                    }
                }
                if (-not $isKnownExample) {
                    $isSyntheticPath = $file.StartsWith("back/tests/") -or $syntheticExamplePaths.Contains($file)
                    if ($isSyntheticPath) {
                        foreach ($example in $knownSyntheticExamples) {
                            if ($match.Line.Contains($example)) {
                                $isKnownExample = $true
                                break
                            }
                        }
                    }
                }
                if ($isKnownExample) {
                    continue
                }
                Add-Finding $findings "review" "public-sensitive-pattern" $file "$($rule.Name) at line $($match.LineNumber)"
            }
        } catch {
            Add-Finding $findings "review" "public-scan-skipped" $file "could not scan as text"
        }
    }
}

$publicEmails = @(
    git -C $Root log --all --format="%H`t%ae`t%ce" 2>$null
)
foreach ($entry in $publicEmails) {
    $parts = $entry -split "`t"
    if ($parts.Count -lt 3) {
        continue
    }
    foreach ($email in $parts[1..2] | Sort-Object -Unique) {
        if ($email -and $email -notmatch '@users\.noreply\.github\.com$') {
            Add-Finding $findings "review" "git-personal-email" $parts[0] "commit metadata exposes $email"
        }
    }
}

$trackedArtifactPatterns = @(
    "\.zip$",
    "\.tar$",
    "\.tar\.gz$",
    "\.sqlite$",
    "\.db$",
    "\.png$",
    "\.jpg$",
    "\.jpeg$",
    "\.gif$",
    "\.webp$",
    "^front/dist/",
    "^front/test-results/",
    "^front/playwright-report/",
    "^back/htmlcov/",
    "^back/uploads/",
    "^back/storage/"
)

$publicArtifactPaths = @(
    "docs/screenshots/desktop-admin.png",
    "docs/screenshots/desktop-home.png",
    "docs/screenshots/desktop-indicators.png",
    "docs/screenshots/mobile-home.png",
    "docs/screenshots/mobile-indicators.png",
    "docs/screenshots/mobile-login.png"
)

foreach ($file in $publicFiles) {
    $fullPath = Join-Path $Root $file
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        continue
    }

    foreach ($pattern in $trackedArtifactPatterns) {
        if ($publicArtifactPaths.Contains($file)) {
            continue
        }
        if ($file -match $pattern) {
            Add-Finding $findings "review" "public-artifact" $file "matches $pattern"
        }
    }
}

$localArtifactPaths = @(
    ".env",
    "back/.env",
    "front/dist",
    "front/playwright-report",
    "front/test-results",
    "front/tests/e2e-results",
    "back/htmlcov",
    "back/test-results",
    "back/storage",
    "back/uploads",
    ".pytest_cache",
    "back/.pytest_cache",
    ".playwright-mcp",
    "test-results"
)

foreach ($path in $localArtifactPaths) {
    $fullPath = Join-Path $Root $path
    if (Test-Path -LiteralPath $fullPath) {
        Add-Finding $findings "block-public-copy" "local-ignored-artifact" $path "exists locally; exclude from public tree and release archives"
    }
}

$readmePath = Join-Path $Root "README.md"
if (Test-Path -LiteralPath $readmePath) {
    $readme = Get-Content -LiteralPath $readmePath -Raw
    $linkMatches = [regex]::Matches($readme, '\[[^\]]+\]\(([^)]+)\)')
    foreach ($linkMatch in $linkMatches) {
        $target = $linkMatch.Groups[1].Value
        if ($target -match '^(https?:|mailto:|#)') {
            continue
        }

        $cleanTarget = ($target -split "#")[0]
        if ([string]::IsNullOrWhiteSpace($cleanTarget)) {
            continue
        }

        $normalized = $cleanTarget -replace "/", [IO.Path]::DirectorySeparatorChar
        $fullTarget = Join-Path $Root $normalized
        if (-not (Test-Path -LiteralPath $fullTarget)) {
            Add-Finding $findings "review" "readme-link-missing" $cleanTarget "README local link target does not exist"
        } elseif (-not (Test-GitPublicCandidate $cleanTarget)) {
            Add-Finding $findings "review" "readme-link-ignored" $cleanTarget "README local link target is ignored; include it in the public allowlist or remove the link"
        }
    }
}

Write-Output "Open source preflight report"
Write-Output "Root: $Root"
Write-Output "Public candidate files scanned: $($publicFiles.Count)"
Write-Output "Findings: $($findings.Count)"

if ($findings.Count -gt 0) {
    $findings |
        Sort-Object Severity, Category, Path |
        Format-Table -AutoSize
}

Write-Output "Read-only check complete. No files were deleted, moved, rewritten, committed, or pushed."
