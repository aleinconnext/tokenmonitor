using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;

namespace TokenMonitor.Windows;

public partial class MainWindow : Window
{
    private readonly Dictionary<string, GaugeControl> _gauges = new();
    private readonly DispatcherTimer _refreshTimer = new() { Interval = TimeSpan.FromSeconds(5) };
    private readonly DispatcherTimer _hidePopupTimer = new() { Interval = TimeSpan.FromMilliseconds(220) };
    private string? _selected;
    private bool _vertical;
    private string _anchor = "top-right";
    private Point _dragStart;
    private bool _trackingDrag;
    private readonly DataCollector _collector = new();
    private readonly Dictionary<string, GaugeData> _data = new();
    private bool _refreshing;

    public MainWindow()
    {
        InitializeComponent();
        CreateGauges();
        CreditIcon.Source = IconAssets.Load("github");
        BuildContextMenu();
        Loaded += async (_, _) => { ApplyOrientation(false); SnapToAnchor("top-right"); await RefreshDataAsync(); };
        _refreshTimer.Tick += async (_, _) => await RefreshDataAsync();
        _hidePopupTimer.Tick += (_, _) => HidePopupIfOutside();
        PreviewMouseLeftButtonDown += BeginDragTracking;
        PreviewMouseMove += TrackDrag;
        PreviewMouseLeftButtonUp += EndDragTracking;
        _refreshTimer.Start();
        DetailsPopup.MouseEnter += (_, _) => _hidePopupTimer.Stop();
        DetailsPopup.MouseLeave += (_, _) => SchedulePopupHide();
        DetailsCard.MouseEnter += (_, _) => _hidePopupTimer.Stop();
        DetailsCard.MouseLeave += (_, _) => SchedulePopupHide();
    }

    private void CreateGauges()
    {
        AddGauge("claude", "Claude Code", "✳", Color.FromRgb(255, 92, 92));
        AddGauge("cursor", "Cursor", "◇", Color.FromRgb(255, 204, 77));
        AddGauge("codex", "Codex", "◎", Color.FromRgb(125, 132, 146));
        AddGauge("freellmapi", "FreeLLMAPI", "•", Color.FromRgb(61, 220, 132));
    }

    private void AddGauge(string id, string label, string glyph, Color color)
    {
        var gauge = new GaugeControl(label, glyph, new SolidColorBrush(color), IconAssets.Load(id));
        gauge.Activated += (_, _) => ShowDetails(id);
        gauge.MouseEnter += (_, _) => { _hidePopupTimer.Stop(); ShowDetails(id); };
        gauge.MouseLeave += (_, _) => SchedulePopupHide();
        _gauges[id] = gauge;
        Gauges.Children.Add(gauge);
    }

    private void ApplyOrientation(bool vertical)
    {
        _vertical = vertical;
        Height = vertical ? 480 : 165;
        Width = vertical ? 110 : 355;
        Card.Padding = vertical
            ? new Thickness(14, 12, 14, 10)
            : new Thickness(14, 12, 14, 10);
        GaugeRow.Height = new GridLength(vertical ? 480 : 120);
        Gauges.Orientation = vertical ? Orientation.Vertical : Orientation.Horizontal;
        Status.Visibility = vertical ? Visibility.Collapsed : Visibility.Visible;
        Credit.Orientation = vertical ? Orientation.Vertical : Orientation.Horizontal;
        CreditLabel.Text = vertical ? "Alessandro Gonçalves\ntokenmonitor" : "Alessandro Gonçalves · aleinconnext/tokenmonitor";
        CreditLabel.TextAlignment = TextAlignment.Center;
        Credit.Margin = vertical ? new Thickness(0, 8, 0, 0) : new Thickness(0, 6, 0, 0);
        CreditIcon.Margin = vertical ? new Thickness(0, 0, 0, 5) : new Thickness(0, 0, 7, 0);
        DetailsPopup.Placement = vertical ? System.Windows.Controls.Primitives.PlacementMode.Right : System.Windows.Controls.Primitives.PlacementMode.Bottom;
        foreach (var gauge in _gauges.Values) gauge.SetVertical(vertical);
    }

    private void BuildContextMenu()
    {
        var menu = new ContextMenu();
        menu.Items.Add(MenuHeader("ANCORAR"));
        AddAnchor(menu, "Topo esquerdo", "top-left");
        AddAnchor(menu, "Topo direito", "top-right");
        AddAnchor(menu, "Base esquerdo", "bottom-left");
        AddAnchor(menu, "Base direito", "bottom-right");
        AddAnchor(menu, "Lateral esquerda", "left");
        AddAnchor(menu, "Lateral direita", "right");
        AddAnchor(menu, "Livre", "free");
        menu.Items.Add(new Separator());
        var freeSettings = new MenuItem { Header = "Configurar FreeLLMAPI..." };
        freeSettings.Click += (_, _) => OpenFreeLlmApiSettings();
        menu.Items.Add(freeSettings);
        menu.Items.Add(new Separator());
        var above = new MenuItem { Header = "Sempre no topo", IsChecked = true, IsCheckable = true };
        above.Click += (_, _) => Topmost = above.IsChecked;
        menu.Items.Add(above);
        menu.Items.Add(new Separator());
        var exit = new MenuItem { Header = "Sair" };
        exit.Click += (_, _) => Close();
        menu.Items.Add(exit);
        Card.ContextMenu = menu;
    }

    private static MenuItem MenuHeader(string text) => new() { Header = text, IsEnabled = false, FontSize = 10 };

    private void AddAnchor(ContextMenu menu, string label, string anchor)
    {
        var item = new MenuItem { Header = label };
        item.Click += (_, _) => SnapToAnchor(anchor);
        menu.Items.Add(item);
    }

    private void SnapToAnchor(string anchor)
    {
        _anchor = anchor;
        var vertical = anchor is "left" or "right" || (_vertical && anchor == "free");
        ApplyOrientation(vertical);
        var area = SystemParameters.WorkArea;
        var margin = 12.0;
        if (anchor.Contains("left")) Left = area.Left + margin;
        else if (anchor.Contains("right")) Left = area.Right - Width - margin;
        else Left = Math.Max(area.Left, Math.Min(Left, area.Right - Width));
        if (anchor.StartsWith("top")) Top = area.Top + margin;
        else if (anchor.StartsWith("bottom")) Top = area.Bottom - Height - margin;
        else Top = Math.Max(area.Top, Math.Min(Top, area.Bottom - Height));
        // Os quatro cantos permanecem horizontais, como na versão Linux.
        // A orientação vertical só é aplicada por uma ancoragem lateral
        // explícita ou após o usuário encaixar o widget em uma lateral.
        // A posição é calculada depois da orientação para preservar a margem
        // da borda quando o widget muda de horizontal para vertical.
    }

    private void BeginDragTracking(object sender, MouseButtonEventArgs e)
    {
        if (e.OriginalSource is DependencyObject source && IsPopupElement(source)) return;
        _dragStart = e.GetPosition(this);
        _trackingDrag = true;
    }

    private void TrackDrag(object sender, MouseEventArgs e)
    {
        if (!_trackingDrag || e.LeftButton != MouseButtonState.Pressed) return;
        var point = e.GetPosition(this);
        if (Math.Abs(point.X - _dragStart.X) < 5 && Math.Abs(point.Y - _dragStart.Y) < 5) return;
        _trackingDrag = false;
        DetailsPopup.IsOpen = false;
        try { DragMove(); } catch (InvalidOperationException) { return; }
        SnapAfterDrag();
    }

    private void EndDragTracking(object sender, MouseButtonEventArgs e) => _trackingDrag = false;

    private static bool IsPopupElement(DependencyObject source)
    {
        while (source is not null)
        {
            if (source is System.Windows.Controls.Primitives.Popup) return true;
            source = VisualTreeHelper.GetParent(source);
        }
        return false;
    }

    private void SnapAfterDrag()
    {
        var area = SystemParameters.WorkArea;
        const double margin = 12;
        const double snap = 40;
        var left = Math.Abs(Left - area.Left);
        var right = Math.Abs(area.Right - (Left + Width));
        var top = Math.Abs(Top - area.Top);
        var bottom = Math.Abs(area.Bottom - (Top + Height));
        var nearest = Math.Min(Math.Min(left, right), Math.Min(top, bottom));

        if (nearest <= snap && (left == nearest || right == nearest))
        {
            ApplyOrientation(true);
            Left = left <= right ? area.Left + margin : area.Right - Width - margin;
            Top = Math.Max(area.Top + margin, Math.Min(Top, area.Bottom - Height - margin));
            _anchor = left <= right ? "left" : "right";
        }
        else if (nearest <= snap)
        {
            ApplyOrientation(false);
            Top = top <= bottom ? area.Top + margin : area.Bottom - Height - margin;
            Left = Math.Max(area.Left + margin, Math.Min(Left, area.Right - Width - margin));
            _anchor = top <= bottom ? "top" : "bottom";
        }
        else
        {
            Left = Math.Max(area.Left, Math.Min(Left, area.Right - Width));
            Top = Math.Max(area.Top, Math.Min(Top, area.Bottom - Height));
            _anchor = "free";
        }
    }

    private async Task RefreshDataAsync()
    {
        if (_refreshing) return;
        _refreshing = true;
        try
        {
            var values = await _collector.CollectAllAsync();
            _data.Clear();
            foreach (var data in values)
            {
                _data[data.Id] = data;
                _gauges[data.Id].SetValue(data.Percent, data.Subtext);
            }
            Status.Text = string.Join("  ·  ", new[] { "claude", "cursor", "codex", "freellmapi" }.Select(id => _data.TryGetValue(id, out var d) ? $"{d.Label} {FormatGaugePercent(d.Percent)}" : $"{id} —"));
        }
        finally { _refreshing = false; }
        if (_selected is not null && DetailsPopup.IsOpen) ShowDetails(_selected);
    }

    private void ShowDetails(string id)
    {
        _selected = id;
        _hidePopupTimer.Stop();
        var gauge = _gauges[id];
        _data.TryGetValue(id, out var data);
        DetailsContent.Children.Clear();
        AddText(gauge.ModelLabel, 15, FontWeights.Bold, Color.FromRgb(233, 237, 245));
        AddText(id switch { "claude" => "Claude Code · janela de 5 horas", "cursor" => "Cursor · uso do ciclo atual", "codex" => "Codex · sessão local", _ => "FreeLLMAPI · roteador local" }, 8, FontWeights.Normal, Color.FromRgb(111, 119, 137));
        AddSeparator();
        AddText("USO ATUAL", 8, FontWeights.Bold, Color.FromRgb(61, 220, 132));
        AddText(data?.Percent is double p ? $"{p:0}%" : "—", 25, FontWeights.Bold, gauge.Accent.Color);
        AddText(data?.Note ?? "dados reais · atualização automática", 9, FontWeights.Normal, Color.FromRgb(150, 160, 180));
        AddSeparator();
        if (id == "freellmapi" && data?.Sections is { Count: > 0 } sections)
        {
            foreach (var section in sections)
            {
                AddText(section.Title, 8, FontWeights.Bold, Color.FromRgb(61, 220, 132));
                foreach (var row in section.Rows) AddText($"{row.Key,-18} {row.Value}", 9, FontWeights.Normal, Color.FromRgb(150, 160, 180));
                AddSeparator();
            }
        }
        else
        {
            AddText("JANELAS", 8, FontWeights.Bold, Color.FromRgb(61, 220, 132));
            foreach (var row in data?.Details ?? []) AddText($"{row.Key,-12} {row.Value}", 9, FontWeights.Normal, Color.FromRgb(150, 160, 180));
            AddSeparator();
            AddText("ATIVIDADE", 8, FontWeights.Bold, Color.FromRgb(61, 220, 132));
        }
        if (data is { Note: not null }) AddText(data.Note, 9, FontWeights.Normal, Color.FromRgb(220, 150, 120));
        AddText("tokenmonitor · .NET/WPF", 8, FontWeights.Normal, Color.FromRgb(108, 118, 138));
        if (id == "freellmapi") AddConfigButton();
        // O alvo é o cartão inteiro, não o gauge. Assim o popup começa fora
        // da janela principal: abaixo/acima no modo horizontal e totalmente
        // à esquerda/direita no modo vertical.
        DetailsPopup.PlacementTarget = Card;
        DetailsPopup.Placement = _anchor switch
        {
            "left" => System.Windows.Controls.Primitives.PlacementMode.Right,
            "right" => System.Windows.Controls.Primitives.PlacementMode.Left,
            "bottom" or "bottom-left" or "bottom-right" => System.Windows.Controls.Primitives.PlacementMode.Top,
            _ => System.Windows.Controls.Primitives.PlacementMode.Bottom
        };
        const double panelGap = 12.0;
        DetailsPopup.HorizontalOffset = _anchor switch
        {
            "left" => panelGap,
            "right" => -panelGap,
            _ => 0
        };
        DetailsPopup.VerticalOffset = _anchor switch
        {
            "bottom" or "bottom-left" or "bottom-right" => -panelGap,
            _ => panelGap
        };
        DetailsPopup.IsOpen = true;
    }

    private void SchedulePopupHide()
    {
        _hidePopupTimer.Stop();
        _hidePopupTimer.Start();
    }

    private void HidePopupIfOutside()
    {
        _hidePopupTimer.Stop();
        if (_selected is null || DetailsPopup.IsMouseOver) return;
        if (_gauges.TryGetValue(_selected, out var gauge) && gauge.IsMouseOver) return;
        DetailsPopup.IsOpen = false;
    }

    private void AddText(string text, double size, FontWeight weight, Color color)
    {
        DetailsContent.Children.Add(new TextBlock { Text = text, FontSize = size, FontWeight = weight, Foreground = new SolidColorBrush(color), Margin = new Thickness(0, 1, 0, 1), TextWrapping = TextWrapping.Wrap });
    }

    private void AddSeparator() => DetailsContent.Children.Add(new Separator { Margin = new Thickness(0, 7, 0, 7), Background = new SolidColorBrush(Color.FromArgb(35, 255, 255, 255)) });

    private void AddConfigButton()
    {
        var button = new Button { Content = "Configurar FreeLLMAPI", Height = 27, Margin = new Thickness(0, 8, 0, 0), Padding = new Thickness(9, 2, 9, 2), HorizontalAlignment = HorizontalAlignment.Left, FontSize = 9, Background = new SolidColorBrush(Color.FromRgb(37, 40, 46)), Foreground = new SolidColorBrush(Color.FromRgb(233, 237, 245)), BorderBrush = new SolidColorBrush(Color.FromArgb(50, 255, 255, 255)) };
        button.Click += (_, _) => OpenFreeLlmApiSettings();
        DetailsContent.Children.Add(button);
    }

    private async void OpenFreeLlmApiSettings()
    {
        DetailsPopup.IsOpen = false;
        var dialog = new FreeLlmApiSettingsWindow(FreeLlmApiSettings.Load()) { Owner = this };
        if (dialog.ShowDialog() == true) await RefreshDataAsync();
    }

    private static string FormatGaugePercent(double? value) => value.HasValue ? $"{value.Value:0}%" : "—";

    private void CardMouseDown(object sender, MouseButtonEventArgs e)
    {
        // O arraste é tratado no PreviewMouse* da janela para funcionar
        // igualmente ao iniciar sobre o cartão, anel ou ícone.
    }
}
