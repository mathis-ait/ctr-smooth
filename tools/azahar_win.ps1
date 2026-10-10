# Pilotage de la fenetre Azahar sans lui voler le focus :
#   azahar_win.ps1 shot <fichier.png>        capture la fenetre (PrintWindow)
#   azahar_win.ps1 key <touche> [<touche>...] envoie des touches (WM_KEYDOWN/UP), ex. A S M RIGHT
param([string]$cmd, [string[]]$rest)
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public static class W {
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h, EnumProc p, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, System.Text.StringBuilder s, int n);
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [StructLayout(LayoutKind.Sequential)] public struct R { public int L, T, Rt, B; }
}
"@
# uniquement l'Azahar du bac a sable : jamais la fenetre de l'utilisateur
$p = Get-Process azahar -ErrorAction Stop | Where-Object { $_.Path -like '*azahar-sandbox*' -and $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $p) { throw 'Azahar du bac a sable introuvable' }
$h = $p.MainWindowHandle
if ($cmd -eq 'shot') {
  $r = New-Object W+R; [W]::GetWindowRect($h, [ref]$r) | Out-Null
  $bmp = New-Object System.Drawing.Bitmap ($r.Rt - $r.L), ($r.B - $r.T)
  $g = [System.Drawing.Graphics]::FromImage($bmp); $dc = $g.GetHdc()
  [W]::PrintWindow($h, $dc, 2) | Out-Null   # PW_RENDERFULLCONTENT
  $g.ReleaseHdc($dc); $bmp.Save($rest[0]); $g.Dispose(); $bmp.Dispose(); Write-Output $rest[0]
} elseif ($cmd -eq 'key') {
  $vk = @{ A=0x41; S=0x53; Z=0x5A; X=0x58; Q=0x51; W=0x57; M=0x4D; N=0x4E; UP=0x26; DOWN=0x28; LEFT=0x25; RIGHT=0x27; T=0x54; G=0x47; F=0x46; H=0x48 }
  # Les touches vont a la fenetre de rendu (enfant) : on les poste a tous les enfants + la principale.
  $targets = New-Object System.Collections.ArrayList; [void]$targets.Add($h)
  $cb = [W+EnumProc]{ param($c, $l) [void]$targets.Add($c); return $true }
  [W]::EnumChildWindows($h, $cb, [IntPtr]::Zero) | Out-Null
  foreach ($k in $rest) {
    $code = $vk[$k.ToUpper()]; if ($null -eq $code) { throw "touche inconnue $k" }
    foreach ($t in $targets) { [W]::PostMessage($t, 0x100, [IntPtr]$code, [IntPtr]1) | Out-Null }
    Start-Sleep -Milliseconds 120
    foreach ($t in $targets) { [W]::PostMessage($t, 0x101, [IntPtr]$code, [IntPtr]0xC0000001) | Out-Null }
    Start-Sleep -Milliseconds 250
  }
  Write-Output "envoye : $($rest -join ' ')"
}
