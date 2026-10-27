using System.Windows;

namespace TokenMonitor.Windows;

public partial class FreeLlmApiSettingsWindow : Window
{
    private readonly FreeLlmApiSettings _settings;
    private bool _showingKey;

    public FreeLlmApiSettingsWindow(FreeLlmApiSettings settings)
    {
        InitializeComponent();
        _settings = settings;
        ApiKeyBox.Password = settings.ApiKey;
        BaseUrlBox.Text = settings.BaseUrl;
        MonitorUrlBox.Text = settings.MonitorUrl;
    }

    private void ToggleKey(object sender, RoutedEventArgs e)
    {
        _showingKey = !_showingKey;
        if (_showingKey) { ApiKeyTextBox.Text = ApiKeyBox.Password; ApiKeyBox.Visibility = Visibility.Collapsed; ApiKeyTextBox.Visibility = Visibility.Visible; }
        else { ApiKeyBox.Password = ApiKeyTextBox.Text; ApiKeyTextBox.Visibility = Visibility.Collapsed; ApiKeyBox.Visibility = Visibility.Visible; }
    }

    private void Save(object sender, RoutedEventArgs e)
    {
        if (!Uri.TryCreate(BaseUrlBox.Text.Trim(), UriKind.Absolute, out var baseUri) || baseUri.Scheme is not ("http" or "https")) { Message.Text = "Informe uma URL base HTTP/HTTPS válida."; return; }
        if (!Uri.TryCreate(MonitorUrlBox.Text.Trim(), UriKind.Absolute, out var monitorUri) || monitorUri.Scheme is not ("http" or "https")) { Message.Text = "Informe uma URL de monitor HTTP/HTTPS válida."; return; }
        _settings.ApiKey = (_showingKey ? ApiKeyTextBox.Text : ApiKeyBox.Password).Trim(); _settings.BaseUrl = baseUri.ToString().TrimEnd('/'); _settings.MonitorUrl = monitorUri.ToString().TrimEnd('/'); _settings.Save(); DialogResult = true; Close();
    }

    private void Cancel(object sender, RoutedEventArgs e) { DialogResult = false; Close(); }
}
