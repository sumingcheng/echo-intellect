# 读取.env文件环境变量
$envFile = Get-Content .env -ErrorAction SilentlyContinue
if ($envFile) {
    foreach ($line in $envFile) {
        # 跳过空行和注释
        if ($line.Trim() -ne "" -and $line.Trim() -notmatch "^#") {
            $keyValue = $line.Split('=', 2)
            if ($keyValue.Length -eq 2) {
                $key = $keyValue[0].Trim()
                $value = $keyValue[1].Trim()
                [Environment]::SetEnvironmentVariable($key, $value, "Process")
                Write-Host "设置环境变量: $key"
            }
        }
    }
} else {
    Write-Host "警告: 未找到.env文件，环境变量可能不完整"
}

# 代理设置
$env:HTTP_PROXY = "http://127.0.0.1:7890"
$env:HTTPS_PROXY = "http://127.0.0.1:7890"

# Python配置
$env:PYTHONUNBUFFERED = "1"     # 无缓冲输出
$env:PYTHONHTTPSVERIFY = "0"    # 忽略SSL验证(仅测试环境)
$env:SSL_CERT_FILE = ""         # 清除SSL证书变量
$env:SSL_CERT_DIR = ""

# 执行主程序
$host.UI.RawUI.FlushInputBuffer()
try {
    Write-Host "启动项目..."
    python -u ./app/main.py
}
finally {
    Write-Host "脚本已终止"
}