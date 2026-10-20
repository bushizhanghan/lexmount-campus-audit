# push-to-github-pages.ps1
# 用法（二选一）：
#   1) 直接带 token：  .\push-to-github-pages.ps1 -Token ghp_xxx -RepoName lexmount-campus-audit
#   2) 先设环境变量：  $env:GH_TOKEN="ghp_xxx"; .\push-to-github-pages.ps1
#
# 作用：创建仓库 → 推送本目录内容 → 开启 GitHub Pages → 打印最终 URL

param(
  [string]$Token = $env:GH_TOKEN,
  [string]$RepoName = "lexmount-campus-audit",
  [string]$Owner = "",
  [string]$Description = "高校官网 AI 可读性巡检 · Lexmount 云平台真实任务挑战投稿作品",
  [switch]$Private
)

$ErrorActionPreference = "Stop"
$SiteDir = $PSScriptRoot

if (-not $Token) {
  Write-Host "缺少 token。请到 https://github.com/settings/tokens 生成一个 classic token，" -ForegroundColor Yellow
  Write-Host "勾选 repo 权限，然后重跑：" -ForegroundColor Yellow
  Write-Host "  .\push-to-github-pages.ps1 -Token ghp_xxxx" -ForegroundColor Cyan
  exit 1
}

$Headers = @{
  Authorization = "Bearer $Token"
  Accept        = "application/vnd.github+json"
  "User-Agent"  = "dsh-agent"
}
$Api = "https://api.github.com"

# ---------- 1. 校验 token，拿用户名 ----------
Write-Host "[1/5] 校验 token ..." -ForegroundColor Cyan
try {
  $me = Invoke-RestMethod -Uri "$Api/user" -Headers $Headers -Method Get
} catch {
  Write-Host "token 无效或网络不通：$($_.Exception.Message)" -ForegroundColor Red
  exit 1
}
$login = $me.login
if (-not $Owner) { $Owner = $login }
Write-Host "      已登录为: $login" -ForegroundColor Green

# ---------- 2. 创建仓库（已存在则复用） ----------
Write-Host "[2/5] 创建仓库 $Owner/$RepoName ..." -ForegroundColor Cyan
$body = @{
  name        = $RepoName
  description = $Description
  private     = [bool]$Private
  has_issues  = $false
  has_wiki    = $false
} | ConvertTo-Json

$repoUrlOk = $false
try {
  $repo = Invoke-RestMethod -Uri "$Api/user/repos" -Headers $Headers -Method Post -Body $body -ContentType "application/json"
  Write-Host "      已创建: $($repo.html_url)" -ForegroundColor Green
  $repoUrlOk = $true
} catch {
  $msg = $_.ErrorDetails.Message
  if ($msg -match "already exists") {
    Write-Host "      仓库已存在，复用" -ForegroundColor Yellow
    $repoUrlOk = $true
  } else {
    Write-Host "      创建失败: $msg" -ForegroundColor Red
    exit 1
  }
}

# ---------- 3. 本地 git init + commit ----------
Write-Host "[3/5] 初始化本地仓库 ..." -ForegroundColor Cyan
Push-Location $SiteDir
try {
  if (-not (Test-Path ".git")) {
    git init -q
    git branch -M main
  }
  # 写 .nojekyll，避免 Jekyll 忽略下划线开头的路径
  if (-not (Test-Path ".nojekyll")) { New-Item -ItemType File -Name ".nojekyll" | Out-Null }

  git add -A
  $status = git status --porcelain
  if ($status) {
    git -c user.name="$login" -c user.email="$login@users.noreply.github.com" `
        commit -q -m "高校官网 AI 可读性巡检 · 投稿材料"
    Write-Host "      已提交" -ForegroundColor Green
  } else {
    Write-Host "      无变更" -ForegroundColor Yellow
  }

  # ---------- 4. 推送 ----------
  Write-Host "[4/5] 推送到 GitHub ..." -ForegroundColor Cyan
  $remote = "https://x-access-token:$Token@github.com/$Owner/$RepoName.git"
  git remote remove origin 2>$null
  git remote add origin $remote
  git push -u origin main --force 2>&1 | ForEach-Object { Write-Host "      $_" }

  # 推送后立刻把 token 从 remote 里去掉，避免留在 .git/config
  git remote set-url origin "https://github.com/$Owner/$RepoName.git"
  Write-Host "      已推送（token 已从 remote 配置中移除）" -ForegroundColor Green
} finally {
  Pop-Location
}

# ---------- 5. 开启 Pages ----------
Write-Host "[5/5] 开启 GitHub Pages ..." -ForegroundColor Cyan
$pagesBody = @{ source = @{ branch = "main"; path = "/" } } | ConvertTo-Json
try {
  Invoke-RestMethod -Uri "$Api/repos/$Owner/$RepoName/pages" -Headers $Headers -Method Post `
    -Body $pagesBody -ContentType "application/json" | Out-Null
  Write-Host "      已开启 Pages" -ForegroundColor Green
} catch {
  $msg = $_.ErrorDetails.Message
  if ($msg -match "already enabled") {
    try {
      Invoke-RestMethod -Uri "$Api/repos/$Owner/$RepoName/pages" -Headers $Headers -Method Put `
        -Body $pagesBody -ContentType "application/json" | Out-Null
      Write-Host "      Pages 已存在，已更新为 main 分支" -ForegroundColor Yellow
    } catch { Write-Host "      更新 Pages 失败: $msg" -ForegroundColor Yellow }
  } else {
    Write-Host "      开启 Pages 失败: $msg" -ForegroundColor Yellow
    Write-Host "      可手动到 Settings → Pages 选择 main 分支" -ForegroundColor Yellow
  }
}

$url = "https://$Owner.github.io/$RepoName/"
Write-Host ""
Write-Host ("=" * 66) -ForegroundColor Green
Write-Host "  完成！" -ForegroundColor Green
Write-Host ("=" * 66) -ForegroundColor Green
Write-Host ""
Write-Host "  仓库地址 : https://github.com/$Owner/$RepoName"
Write-Host "  作品链接 : $url"
Write-Host "  报告直链 : ${url}report.html"
Write-Host ""
Write-Host "  注意：Pages 首次生效通常需要 1-3 分钟，稍等再打开。" -ForegroundColor Yellow
Write-Host "  提交投稿表单时，把作品链接填成：" -ForegroundColor Yellow
Write-Host "    $url" -ForegroundColor Cyan
