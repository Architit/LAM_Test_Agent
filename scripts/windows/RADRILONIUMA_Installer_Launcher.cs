using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Windows.Forms;

namespace RadriloniumaInstaller
{
    internal static class Program
    {
        [STAThread]
        private static int Main(string[] args)
        {
            try
            {
                string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                bool silentMode = args.Any(a => string.Equals(a, "/S", StringComparison.OrdinalIgnoreCase));
                string scriptFile = silentMode ? "portable_activate.ps1" : "installer_wizard.ps1";
                string scriptPath = Path.Combine(baseDir, scriptFile);
                if (!File.Exists(scriptPath))
                {
                    MessageBox.Show(scriptFile + " not found рядом с EXE.", "RADRILONIUMA Installer", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    return 2;
                }

                var mapped = args.ToList();
                if (silentMode)
                {
                    mapped.RemoveAll(a => string.Equals(a, "/S", StringComparison.OrdinalIgnoreCase));
                    mapped.Add("-Silent");
                    mapped.Add("-AssumeConsent");
                    if (!mapped.Any(a => a.StartsWith("-Mode", StringComparison.OrdinalIgnoreCase)))
                    {
                        mapped.Add("-Mode");
                        mapped.Add("install");
                    }
                }

                string extraArgs = string.Join(" ", mapped.Select(EscapeArg));
                string psArgs = "-ExecutionPolicy Bypass -File \"" + scriptPath + "\" " + extraArgs;

                var psi = new ProcessStartInfo
                {
                    FileName = "powershell.exe",
                    Arguments = psArgs,
                    UseShellExecute = false,
                    CreateNoWindow = false,
                    WorkingDirectory = baseDir
                };

                using (var p = Process.Start(psi))
                {
                    if (p == null)
                    {
                        MessageBox.Show("Не удалось запустить powershell.exe", "RADRILONIUMA Installer", MessageBoxButtons.OK, MessageBoxIcon.Error);
                        return 3;
                    }
                    p.WaitForExit();
                    return p.ExitCode;
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.Message, "RADRILONIUMA Installer", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 1;
            }
        }

        private static string EscapeArg(string value)
        {
            if (string.IsNullOrEmpty(value))
            {
                return "\"\"";
            }
            return "\"" + value.Replace("\"", "\\\"") + "\"";
        }
    }
}
