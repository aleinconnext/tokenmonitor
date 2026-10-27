using System.Globalization;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;

namespace TokenMonitor.Windows;

public sealed class GaugeControl : FrameworkElement
{
    public string ModelLabel { get; }
    public string IconGlyph { get; }
    public ImageSource? IconImage { get; }
    public SolidColorBrush Accent { get; }
    public string Subtext { get; private set; } = "—";
    public double? Value { get; private set; }

    public event EventHandler? Activated;

    public GaugeControl(string label, string glyph, SolidColorBrush accent, ImageSource? iconImage = null)
    {
        ModelLabel = label;
        IconGlyph = glyph;
        Accent = accent;
        IconImage = iconImage;
        Width = 92;
        Height = 120;
        Cursor = Cursors.Hand;
        MouseLeftButtonUp += (_, _) => Activated?.Invoke(this, EventArgs.Empty);
    }

    public void SetValue(double? value, string subtext)
    {
        Value = value.HasValue ? Math.Clamp(value.Value, 0, 100) : null;
        Subtext = string.IsNullOrWhiteSpace(subtext) ? "—" : subtext;
        InvalidateVisual();
    }

    public void SetVertical(bool vertical)
    {
        Width = 92;
        Height = 120;
        InvalidateVisual();
    }

    protected override void OnRender(DrawingContext dc)
    {
        base.OnRender(dc);
        var center = new Point(46, 46);
        const double radius = 37;
        var track = new Pen(new SolidColorBrush(Color.FromRgb(38, 43, 53)), 8);
        var active = new Pen(Accent, 8) { StartLineCap = PenLineCap.Round, EndLineCap = PenLineCap.Round };
        dc.DrawEllipse(null, track, center, radius, radius);
        if (Value is > 0)
        {
            var start = -135.0;
            var end = start + 270.0 * Value!.Value / 100.0;
            var geometry = new StreamGeometry();
            using (var ctx = geometry.Open())
            {
                var startPoint = PointOnCircle(center, radius, start);
                var endPoint = PointOnCircle(center, radius, end);
                ctx.BeginFigure(startPoint, false, false);
                ctx.ArcTo(endPoint, new Size(radius, radius), 0, end - start > 180, SweepDirection.Clockwise, true, false);
            }
            geometry.Freeze();
            dc.DrawGeometry(null, active, geometry);
        }

        if (IconImage is not null)
        {
            dc.DrawImage(IconImage, new Rect(center.X - 21, center.Y - 21, 42, 42));
        }
        else
        {
            var icon = new FormattedText(IconGlyph, CultureInfo.InvariantCulture, FlowDirection.LeftToRight,
                new Typeface("Segoe UI Symbol"), 28, Brushes.White, VisualTreeHelper.GetDpi(this).PixelsPerDip);
            dc.DrawText(icon, new Point(center.X - icon.Width / 2, center.Y - icon.Height / 2 - 2));
        }

        var sub = new FormattedText(Subtext, CultureInfo.InvariantCulture, FlowDirection.LeftToRight,
            new Typeface("Segoe UI"), 8, new SolidColorBrush(Color.FromRgb(111, 119, 137)), VisualTreeHelper.GetDpi(this).PixelsPerDip);
        dc.DrawText(sub, new Point(center.X - sub.Width / 2, 77));
        var pct = new FormattedText(Value is null ? "—" : $"{Value:0}%", CultureInfo.InvariantCulture,
            FlowDirection.LeftToRight, new Typeface("Segoe UI Semibold"), 12, Accent, VisualTreeHelper.GetDpi(this).PixelsPerDip);
        dc.DrawText(pct, new Point(center.X - pct.Width / 2, 105));
    }

    private static Point PointOnCircle(Point center, double radius, double angle)
    {
        var radians = angle * Math.PI / 180.0;
        return new Point(center.X + radius * Math.Cos(radians), center.Y + radius * Math.Sin(radians));
    }
}
