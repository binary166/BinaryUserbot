import asyncio
import os
import shutil
import subprocess
from pathlib import Path


def _powershell_path() -> str:
    return shutil.which("pwsh") or shutil.which("powershell") or "powershell"


def _windows_script(command: str) -> str:
    return "\n".join(
        [
            "$ErrorActionPreference = 'Continue'",
            "$ProgressPreference = 'SilentlyContinue'",
            "[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)",
            "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)",
            "$OutputEncoding = [System.Text.UTF8Encoding]::new($false)",
            "Remove-Item Alias:ls -Force -ErrorAction SilentlyContinue",
            "Remove-Item Alias:ll -Force -ErrorAction SilentlyContinue",
            "Remove-Item Alias:pwd -Force -ErrorAction SilentlyContinue",
            (
                "function ls { param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Items) "
                "$force=$false; $long=$false; $paths=@(); "
                "foreach ($item in $Items) { "
                "if ($item -match '^-') { if ($item.Contains('a')) { $force=$true }; if ($item.Contains('l')) { $long=$true } } "
                "else { $paths += $item } } "
                "if ($paths.Count -eq 0) { $paths=@('.') } "
                "foreach ($path in $paths) { "
                "Get-ChildItem -Path $path -Force:$force | ForEach-Object { "
                "$name=$_.Name; if ($_.PSIsContainer) { $name = \"$name/\" }; "
                "if ($long) { $size = if ($_.PSIsContainer) { '<DIR>' } else { $_.Length }; "
                "'{0,12} {1:yyyy-MM-dd HH:mm} {2}' -f $size, $_.LastWriteTime, $name } else { $name } } } }"
            ),
            "function la { ls -a @args }",
            "function ll { ls -la @args }",
            "function pwd { (Get-Location).Path }",
            "function head { param([int]$n=10, [Parameter(ValueFromPipeline=$true)]$InputObject) begin{$i=0} process{ if($i -lt $n){$InputObject; $i++} } }",
            "function tail { param([int]$n=10, [Parameter(ValueFromPipeline=$true)]$InputObject) begin{$buf=@()} process{$buf += $InputObject} end{$buf | Select-Object -Last $n} }",
            "function grep { Select-String @args }",
            (
                "function touch { foreach ($path in $args) { "
                "if (Test-Path -LiteralPath $path) { "
                "(Get-Item -LiteralPath $path).LastWriteTime = Get-Date "
                "} else { New-Item -ItemType File -Path $path | Out-Null } } }"
            ),
            "function which { Get-Command @args | Select-Object -ExpandProperty Source }",
            "function uname { if ($args -contains '-a') { [Environment]::OSVersion.VersionString } else { 'Windows' } }",
            command,
        ]
    )


def terminal_args(command: str) -> list[str]:
    if os.name == "nt":
        return [
            _powershell_path(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            _windows_script(command),
        ]
    return [os.environ.get("SHELL") or "/bin/sh", "-lc", command]


def decode_terminal_output(data: bytes) -> str:
    if not data:
        return ""
    if data.startswith((b"\xff\xfe", b"\xfe\xff")) or data.count(b"\x00") > max(2, len(data) // 6):
        for encoding in ("utf-16", "utf-16le"):
            try:
                return _normalize_newlines(data.decode(encoding))
            except UnicodeDecodeError:
                continue
    for encoding in ("utf-8-sig", "utf-8", "cp866", "cp1251"):
        try:
            return _normalize_newlines(data.decode(encoding))
        except UnicodeDecodeError:
            continue
    return _normalize_newlines(data.decode("utf-8", errors="replace"))


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\r\n", "\n").replace("\r\n", "\n").replace("\r", "\n")


async def spawn_terminal_process(command: str, cwd: str | Path | None = None):
    kwargs = {}
    if cwd is not None:
        kwargs["cwd"] = str(cwd)
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return await asyncio.create_subprocess_exec(
        *terminal_args(command),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        **kwargs,
    )
