using System.Drawing;
using System.Drawing.Drawing2D;
using Forms = System.Windows.Forms;

namespace TokenMonitor.Windows;

internal sealed class TrayIcon : IDisposable
{
    private readonly MainWindow _window;
    private readonly Forms.NotifyIcon _notifyIcon;
    private readonly Forms.ContextMenuStrip _menu;
    private readonly Bitmap _bitmap;
    private readonly Icon _icon;
    private bool _disposed;

    public TrayIcon(MainWindow window)
    {
        _window = window;
        _bitmap = CreateLinuxStyleIcon();
        _icon = Icon.FromHandle(_bitmap.GetHicon());
        _notifyIcon = new Forms.NotifyIcon
        {
            Icon = _icon,
            Text = "TokenMonitor",
            Visible = true
        };
        _notifyIcon.DoubleClick += (_, _) => ShowWidget();

        _menu = new Forms.ContextMenuStrip();
        _menu.Items.Add("Abrir TokenMonitor", null, (_, _) => ShowWidget());
        _menu.Items.Add(new Forms.ToolStripSeparator());
        _menu.Items.Add("Sair", null, (_, _) => System.Windows.Application.Current.Shutdown());
        _notifyIcon.ContextMenuStrip = _menu;
    }

    private void ShowWidget()
    {
        if (!_window.Dispatcher.CheckAccess())
        {
            _window.Dispatcher.BeginInvoke(ShowWidget);
            return;
        }
        _window.Show();
        _window.Topmost = true;
        _window.Activate();
    }

    private static Bitmap CreateLinuxStyleIcon()
    {
        var bitmap = new Bitmap(32, 32, System.Drawing.Imaging.PixelFormat.Format32bppArgb);
        using var graphics = Graphics.FromImage(bitmap);
        graphics.SmoothingMode = SmoothingMode.AntiAlias;
        graphics.Clear(Color.Transparent);

        using var background = new SolidBrush(Color.FromArgb(245, 17, 19, 24));
        using var border = new Pen(Color.FromArgb(255, 35, 40, 51), 1);
        graphics.FillRoundedRectangle(background, 1, 1, 30, 30, 7);
        graphics.DrawRoundedRectangle(border, 1, 1, 30, 30, 7);

        using var track = new Pen(Color.FromArgb(255, 38, 42, 51), 3);
        using var yellow = new Pen(Color.FromArgb(255, 255, 204, 77), 3) { StartCap = LineCap.Round, EndCap = LineCap.Round };
        using var green = new Pen(Color.FromArgb(255, 61, 220, 132), 3) { StartCap = LineCap.Round, EndCap = LineCap.Round };
        graphics.DrawArc(track, 3, 6, 11, 11, 135, 270);
        graphics.DrawArc(yellow, 3, 6, 11, 11, 135, 170);
        graphics.DrawArc(track, 18, 6, 11, 11, 135, 270);
        graphics.DrawArc(green, 18, 6, 11, 11, 135, 110);
        return bitmap;
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        _notifyIcon.Visible = false;
        _notifyIcon.Dispose();
        _menu.Dispose();
        _icon.Dispose();
        _bitmap.Dispose();
    }
}

internal static class GraphicsExtensions
{
    public static void FillRoundedRectangle(this Graphics graphics, Brush brush, float x, float y, float width, float height, float radius)
    {
        using var path = RoundedRectangle(x, y, width, height, radius);
        graphics.FillPath(brush, path);
    }

    public static void DrawRoundedRectangle(this Graphics graphics, Pen pen, float x, float y, float width, float height, float radius)
    {
        using var path = RoundedRectangle(x, y, width, height, radius);
        graphics.DrawPath(pen, path);
    }

    private static GraphicsPath RoundedRectangle(float x, float y, float width, float height, float radius)
    {
        var path = new GraphicsPath();
        var diameter = radius * 2;
        path.AddArc(x, y, diameter, diameter, 180, 90);
        path.AddArc(x + width - diameter, y, diameter, diameter, 270, 90);
        path.AddArc(x + width - diameter, y + height - diameter, diameter, diameter, 0, 90);
        path.AddArc(x, y + height - diameter, diameter, diameter, 90, 90);
        path.CloseFigure();
        return path;
    }
}
