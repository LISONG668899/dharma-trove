# 藏汉佛教精华 · DharmaTrove
# 一键发布：扫描【桌面】上命名为「类目_标题.md」的文章（Claude 转换好后你直接存到桌面的文件），
#          自动放进对应类目文件夹、更新该类目首页的文章列表、
#          推送到 GitHub 触发网站自动部署，最后清空存档。
#
# 也兼容「类目_标题.txt」（如果你自己直接写纯文本，脚本会自动生成 frontmatter，
# 但正文里像长引文、偈颂代码块这类排版规矩需要你自己在 txt 里写好）。
#
# 处理成功后，文件会从桌面上消失——这就是"已经处理并发布好"的信号。

$repoRoot = $PSScriptRoot
$desktop = [Environment]::GetFolderPath("Desktop")
$inbox = Join-Path $repoRoot "待发布"
$docsRoot = Join-Path $repoRoot "docs"
$categories = @("唯识", "中观", "华严", "禅宗", "净土", "大手印", "大圆满", "综合")

Write-Host "======================================"
Write-Host "  藏汉佛教精华 · 一键发布"
Write-Host "======================================"
Write-Host ""

if (-not (Test-Path $inbox)) {
    New-Item -ItemType Directory -Path $inbox | Out-Null
}

# 扫描桌面上文件名符合「类目_标题」格式（.txt 或 .md）的文件，
# 桌面上其他不相关的文件不会被碰
$candidates = Get-ChildItem -Path $desktop -File | Where-Object {
    ($_.Extension -eq ".txt" -or $_.Extension -eq ".md") -and
    (($_.BaseName -split "_", 2).Count -ge 2) -and
    ($categories -contains (($_.BaseName -split "_", 2)[0].Trim()))
}

if ($candidates.Count -eq 0) {
    Write-Host "桌面上没有找到命名为「类目_标题.txt」或「类目_标题.md」的文章。"
    Write-Host "请把要发布的文章放在桌面上，文件名格式例如「大手印_降雷大手印导论.txt」。"
    Write-Host ""
    Write-Host "提示：如果是从 Word 写的，请先「另存为」纯文本 .txt，编码选 UTF-8。"
    Pause
    exit
}

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
$generated = @()

foreach ($file in $candidates) {

    $name = $file.BaseName
    $parts = $name -split "_", 2
    $category = $parts[0].Trim()
    $titleFromName = $parts[1].Trim()

    $rawContent = Get-Content -Path $file.FullName -Raw -Encoding UTF8

    if ($file.Extension -eq ".md") {
        # 已经是成品 MD，直接使用；从 frontmatter 里取 title/date 用于目录列表，取不到就用文件名/今天日期兜底
        $content = $rawContent
        $titleMatch = [regex]::Match($content, '(?m)^title:\s*(.+)$')
        $dateMatch = [regex]::Match($content, '(?m)^date:\s*(.+)$')
        $title = if ($titleMatch.Success) { $titleMatch.Groups[1].Value.Trim() } else { $titleFromName }
        $date = if ($dateMatch.Success) { $dateMatch.Groups[1].Value.Trim() } else { Get-Date -Format "yyyy-MM-dd" }
    }
    else {
        # .txt 文件：自动生成 frontmatter + 标题，正文开头可选的「日期：」「作者：」两行自动识别抽走
        $title = $titleFromName
        $date = Get-Date -Format "yyyy-MM-dd"
        $author = $null

        $lines = $rawContent -split "`r`n|`n"
        $bodyStartIndex = 0

        foreach ($i in 0..([Math]::Min(1, $lines.Count - 1))) {
            $line = $lines[$i].Trim()
            if ($line -match '^日期[:：]\s*(.+)$') {
                $date = $Matches[1].Trim()
                $bodyStartIndex = $i + 1
            }
            elseif ($line -match '^作者[:：]\s*(.+)$') {
                $author = $Matches[1].Trim()
                $bodyStartIndex = $i + 1
            }
        }

        $bodyLines = $lines[$bodyStartIndex..($lines.Count - 1)]
        # 去掉正文开头多余的空行
        while ($bodyLines.Count -gt 0 -and $bodyLines[0].Trim() -eq "") {
            $bodyLines = $bodyLines[1..($bodyLines.Count - 1)]
        }
        $body = $bodyLines -join "`n"

        $frontmatterLines = @("---", "title: $title", "date: $date")
        if ($author) { $frontmatterLines += "author: $author" }
        $frontmatterLines += "---"

        $content = ($frontmatterLines -join "`n") + "`n`n# $title`n`n" + $body + "`n"
    }

    $targetDir = Join-Path $docsRoot $category
    if (-not (Test-Path $targetDir)) {
        Write-Host "[跳过] 「$($file.Name)」—— 找不到对应的类目文件夹 docs\$category，文件留在桌面未处理"
        continue
    }

    $targetPath = Join-Path $targetDir "$title.md"

    if (Test-Path $targetPath) {
        Write-Host "[提示] 「$category」下已存在同名文章「$title.md」，本次将覆盖更新其内容。"
    }

    [System.IO.File]::WriteAllText($targetPath, $content, $utf8NoBom)

    # 更新该类目首页的文章列表（避免重复添加同一篇）
    $indexPath = Join-Path $targetDir "index.md"
    $indexContent = Get-Content -Path $indexPath -Raw -Encoding UTF8
    $linkHref = "/$category/$title"
    $newLine = "  <li><a href=`"$linkHref`">$title</a><span class=`"dt-article-date`">$date</span></li>"

    if ($indexContent -notmatch [regex]::Escape($linkHref)) {
        $indexContent = $indexContent -replace '</ul>', "$newLine`n</ul>"
        [System.IO.File]::WriteAllText($indexPath, $indexContent, $utf8NoBom)
    }

    # 把桌面上的原文件挪进「待发布」文件夹（桌面上文件消失 = 处理成功）
    $archivePath = Join-Path $inbox $file.Name
    Move-Item -Path $file.FullName -Destination $archivePath -Force

    Write-Host "[已生成] 「$category」/「$title」（日期：$date）—— 已从桌面移入待发布文件夹"
    $generated += "$category/$title"
}

Write-Host ""
if ($generated.Count -eq 0) {
    Write-Host "没有成功生成任何文章，本次不执行推送。"
    Pause
    exit
}

Write-Host "本次共处理 $($generated.Count) 篇：$($generated -join '、')"
Write-Host ""
Write-Host "正在推送到 GitHub 并触发自动部署..."
Write-Host ""

Set-Location $repoRoot
git add .
$commitMsg = "发布文章：" + ($generated -join "、")
git commit -m $commitMsg
git push

# 推送后清空待发布文件夹里的存档 .md/.txt 文件（说明.txt 保留）
Get-ChildItem -Path $inbox -File | Where-Object { $_.Name -ne "说明.txt" } | Remove-Item -Force

Write-Host ""
Write-Host "======================================"
Write-Host "全部完成！本次发布：$($generated -join '、')"
Write-Host "Cloudflare Pages 会在一两分钟内自动完成部署。"
Write-Host "======================================"
Pause
