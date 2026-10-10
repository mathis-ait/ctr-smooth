# Place la fenetre de l'Azahar portable (bac a sable) petite, dans le coin bas-droit
# de l'ecran le plus a gauche, tout au fond de la pile des fenetres, sans l'activer.
# Elle doit rester sur un ecran : hors ecran, Azahar ne lit plus la manette (SDL).
# Cachee derriere d'autres fenetres, elle recoit la manette et reste capturable.
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System; using System.Runtime.InteropServices;
public static class Off {
  [StructLayout(LayoutKind.Sequential)] public struct P { public int x, y; }
  [StructLayout(LayoutKind.Sequential)] public struct R { public int L, T, Rt, B; }
  [StructLayout(LayoutKind.Sequential)] public struct WP { public int len, flags, show; public P min, max; public R normal; }
  [DllImport("user32.dll")] public static extern bool SetWindowPlacement(IntPtr h, ref WP p);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint f);
}
"@
$scr = [System.Windows.Forms.Screen]::AllScreens | Sort-Object { $_.Bounds.Left } | Select-Object -First 1
$x = $scr.Bounds.Right - 830
$y = $scr.Bounds.Bottom - 800
for ($i = 0; $i -lt 40; $i++) {
  $p = Get-Process azahar -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*azahar-sandbox*' -and $_.MainWindowHandle -ne 0 } | Select-Object -First 1
  if ($p) { break }
  Start-Sleep -Milliseconds 250
}
if (-not $p) { Write-Output "fenetre introuvable"; exit 1 }
$h = $p.MainWindowHandle
$wp = New-Object Off+WP; $wp.len = [Runtime.InteropServices.Marshal]::SizeOf($wp); $wp.show = 4
$wp.normal.L = $x; $wp.normal.T = $y; $wp.normal.Rt = $x + 827; $wp.normal.B = $y + 757
[Off]::SetWindowPlacement($h, [ref]$wp) | Out-Null
[Off]::SetWindowPos($h, [IntPtr]1, $x, $y, 827, 757, 0x0010) | Out-Null
Write-Output "fenetre placee en $x,$y (fond de pile)"
