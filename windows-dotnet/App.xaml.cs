using System.IO;
using System.Text;
using System.Windows;
using System.Windows.Threading;

namespace TokenMonitor.Windows;

public partial class App : Application
{
    public App()
    {
        DispatcherUnhandledException += OnDispatcherUnhandledException;
        AppDomain.CurrentDomain.UnhandledException += OnUnhandledException;
        TaskScheduler.UnobservedTaskException += OnUnobservedTaskException;
    }

    protected override void OnStartup(StartupEventArgs e)
    {
        try
        {
            base.OnStartup(e);
            var window = new MainWindow();
            MainWindow = window;
            window.Show();
        }
        catch (Exception ex)
        {
            Report(ex);
            MessageBox.Show(
                "O TokenMonitor não conseguiu iniciar.\n\n" + ex.Message +
                "\n\nLog: " + LogPath(),
                "TokenMonitor - erro", MessageBoxButton.OK, MessageBoxImage.Error);
            Shutdown(1);
        }
    }

    private void OnDispatcherUnhandledException(object sender, DispatcherUnhandledExceptionEventArgs e)
    {
        Report(e.Exception);
        e.Handled = true;
        MessageBox.Show("Erro do TokenMonitor:\n\n" + e.Exception.Message +
                        "\n\nLog: " + LogPath(), "TokenMonitor - erro",
                        MessageBoxButton.OK, MessageBoxImage.Error);
    }

    private static void OnUnhandledException(object sender, UnhandledExceptionEventArgs e)
    {
        if (e.ExceptionObject is Exception ex) Report(ex);
    }

    private static void OnUnobservedTaskException(object? sender, UnobservedTaskExceptionEventArgs e)
    {
        Report(e.Exception);
        e.SetObserved();
    }

    private static string LogPath()
    {
        return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "TokenMonitor", "error.log");
    }

    private static void Report(Exception ex)
    {
        try
        {
            var path = LogPath();
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            File.AppendAllText(path,
                $"[{DateTime.Now:O}] {ex}\n\n",
                Encoding.UTF8);
        }
        catch
        {
            // Logging must never become a second startup failure.
        }
    }
}
