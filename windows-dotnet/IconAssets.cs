using System.IO;
using System.Text.RegularExpressions;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace TokenMonitor.Windows;

internal static class IconAssets
{
    private static readonly Dictionary<string, ImageSource?> Cache = new();

    public static ImageSource? Load(string id)
    {
        if (Cache.TryGetValue(id, out var cached)) return cached;
        try
        {
            var source = Path.Combine(AppContext.BaseDirectory, "tokenmon.py");
            if (!File.Exists(source)) return null;
            var text = File.ReadAllText(source);
            var pattern = id == "github"
                ? "GITHUB_ICON_B64\\s*=\\s*\\\"(?<data>[A-Za-z0-9+/=]+)\\\""
                : $"\\\"{Regex.Escape(id)}\\\"\\s*:\\s*\\(\\s*\\\"(?<data>[A-Za-z0-9+/=]+)\\\"";
            var match = Regex.Match(text, pattern, RegexOptions.CultureInvariant);
            if (!match.Success) return null;
            var bytes = Convert.FromBase64String(match.Groups["data"].Value);
            using var stream = new MemoryStream(bytes);
            var image = new BitmapImage();
            image.BeginInit();
            image.CacheOption = BitmapCacheOption.OnLoad;
            image.StreamSource = stream;
            image.EndInit();
            image.Freeze();
            Cache[id] = image;
            return image;
        }
        catch
        {
            Cache[id] = null;
            return null;
        }
    }
}
