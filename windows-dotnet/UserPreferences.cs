using Microsoft.Win32;
using System.IO;
using System.Text.Json;

namespace TokenMonitor.Windows;

internal sealed class UserPreferences
{
    public string Anchor { get; set; } = "top-right";
    public double? Left { get; set; }
    public double? Top { get; set; }
    public bool Topmost { get; set; } = true;
}

internal static class UserPreferencesStore
{
    private const string RunKeyPath = @"Software\Microsoft\Windows\CurrentVersion\Run";
    private const string RunValueName = "TokenMonitor";

    private static string DirectoryPath => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "TokenMonitor");

    private static string FilePath => Path.Combine(DirectoryPath, "settings.json");

    public static UserPreferences Load()
    {
        try
        {
            if (File.Exists(FilePath))
            {
                var settings = JsonSerializer.Deserialize<UserPreferences>(File.ReadAllText(FilePath));
                if (settings is not null) return settings;
            }
        }
        catch
        {
            // Prefer the default placement if a previous settings file is invalid.
        }

        return new UserPreferences();
    }

    public static void Save(UserPreferences settings)
    {
        try
        {
            Directory.CreateDirectory(DirectoryPath);
            File.WriteAllText(FilePath, JsonSerializer.Serialize(settings, new JsonSerializerOptions { WriteIndented = true }));
        }
        catch
        {
            // Preferences must never prevent the widget from opening.
        }
    }

    public static bool StartsWithWindows
    {
        get
        {
            try
            {
                using var key = Registry.CurrentUser.OpenSubKey(RunKeyPath);
                return key?.GetValue(RunValueName) is string value &&
                       string.Equals(value.Trim('"'), Environment.ProcessPath, StringComparison.OrdinalIgnoreCase);
            }
            catch { return false; }
        }
    }

    public static void SetStartsWithWindows(bool enabled)
    {
        try
        {
            using var key = Registry.CurrentUser.CreateSubKey(RunKeyPath);
            if (enabled)
            {
                var executable = Environment.ProcessPath;
                if (!string.IsNullOrWhiteSpace(executable)) key.SetValue(RunValueName, $"\"{executable}\"");
            }
            else
            {
                key.DeleteValue(RunValueName, false);
            }
        }
        catch
        {
            // The option remains safe to use even if Windows policy blocks the registry write.
        }
    }
}
