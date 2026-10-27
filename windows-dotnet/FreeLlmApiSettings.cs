using System.IO;
using System.Text.Json;

namespace TokenMonitor.Windows;

public sealed class FreeLlmApiSettings
{
    public string ApiKey { get; set; } = "";
    public string BaseUrl { get; set; } = "http://127.0.0.1:31415/v1";
    public string MonitorUrl { get; set; } = "http://127.0.0.1:31415/v1";
    private static string PathName => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "TokenMonitor", "freellmapi.json");
    public static FreeLlmApiSettings Load() { try { if (File.Exists(PathName)) return JsonSerializer.Deserialize<FreeLlmApiSettings>(File.ReadAllText(PathName)) ?? new(); } catch { } return new(); }
    public void Save() { Directory.CreateDirectory(Path.GetDirectoryName(PathName)!); File.WriteAllText(PathName, JsonSerializer.Serialize(this, new JsonSerializerOptions { WriteIndented = true })); }
}
