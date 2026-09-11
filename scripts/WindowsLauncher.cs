using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Windows.Forms;

// A stable, framework-only bootstrapper: application sources stay outside the EXE.
internal static class WindowsLauncher
{
    [STAThread]
    private static int Main(string[] args)
    {
        bool check = args.Length == 1 && args[0] == "--check";
        string root = AppDomain.CurrentDomain.BaseDirectory;
        string logs = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "SuperPresenter", "logs");
        string log = Path.Combine(logs, "launcher.log");
        try
        {
            Directory.CreateDirectory(logs);
            File.WriteAllText(log, DateTime.Now.ToString("s") + " Starting in " + root + Environment.NewLine, Encoding.UTF8);
            string python = Path.Combine(root, ".venv", "Scripts", "python.exe");
            if (!File.Exists(python))
                throw new Exception("Chybi Python prostredi .venv. Spustte pripravit_prostredi.bat ve slozce aplikace. Podrobnosti jsou v README.md.");
            string script = Path.Combine(root, "super_presenter.py");
            if (!File.Exists(script))
                throw new Exception("EXE musi zustat ve slozce projektu vedle super_presenter.py.");
            int result = Run(python, "-c \"import sys, tkinter, PIL, screeninfo; assert sys.version_info >= (3, 10), 'Python 3.10+ required'; import superpresenter.app\"", root, log);
            if (result != 0)
                throw new Exception("Python nebo zavislosti nejsou v poradku. Spustte pripravit_prostredi.bat.");
            if (check) return 0;
            result = Run(python, Quote(script), root, log);
            if (result != 0) throw new Exception("Aplikace skoncila s chybou (kod " + result + ").");
            return 0;
        }
        catch (Exception ex)
        {
            try { File.AppendAllText(log, ex.ToString() + Environment.NewLine, Encoding.UTF8); } catch { }
            if (!check) MessageBox.Show(ex.Message + "\n\nDiagnostika: " + log, "SuperPresenter", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    private static string Quote(string value) { return "\"" + value + "\""; }

    private static int Run(string executable, string arguments, string root, string log)
    {
        var info = new ProcessStartInfo(executable, arguments) {
            WorkingDirectory = root, UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardOutput = true, RedirectStandardError = true
        };
        info.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
        info.EnvironmentVariables["PYTHONUNBUFFERED"] = "1";
        info.StandardOutputEncoding = Encoding.UTF8;
        info.StandardErrorEncoding = Encoding.UTF8;
        using (var writer = new StreamWriter(log, true, Encoding.UTF8))
        using (var process = new Process { StartInfo = info })
        {
            DataReceivedEventHandler record = (sender, e) => {
                if (e.Data != null) lock (writer) { writer.WriteLine(e.Data); writer.Flush(); }
            };
            process.OutputDataReceived += record;
            process.ErrorDataReceived += record;
            process.Start();
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();
            process.WaitForExit();
            return process.ExitCode;
        }
    }
}
