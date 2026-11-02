using System.Text.Json;
using System.Text.Json.Serialization;
using Dbce.TripleScreen;

namespace Fh2.Triples;

public sealed record PanelConfig(string Id, int WidthPx, int HeightPx, double WidthMm,
    double HeightMm, double CurveRadiusMm = 0, double FoldDegrees = 0);

// Raw physical measurements only. A plan is transient, never saved in this config.
public sealed record TripleConfig
{
    public required int SchemaVersion { get; init; }
    public bool Enabled { get; init; }
    public int DesktopX { get; init; }
    public int DesktopY { get; init; }
    public required int CenterIndex { get; init; }
    public required double EyeDistanceMm { get; init; }
    public double EyeHeightMm { get; init; }
    public double BezelGapMm { get; init; }
    public required PanelConfig[] Displays { get; init; }
    public CameraStarts Starts { get; init; } = new();

    public RigDefinition Rig()
    {
        if (SchemaVersion != 1) throw new ArgumentException("Unsupported FH2 triple config version.");
        if (Displays is null || Displays.Length is < 1 or > 16 || Starts is null)
            throw new ArgumentException("Require 1-16 displays and camera starting choices.");
        foreach (double v in new[] { EyeDistanceMm, EyeHeightMm, BezelGapMm })
            if (!double.IsFinite(v)) throw new ArgumentException("Rig values must be finite.");
        var ids = new HashSet<string>(StringComparer.Ordinal);
        var specs = new List<DisplaySpec>();
        int width = 0;
        foreach (var d in Displays)
        {
            if (d is null || string.IsNullOrWhiteSpace(d.Id) || !ids.Add(d.Id))
                throw new ArgumentException("Display IDs must be nonempty and unique.");
            foreach (double v in new[] { d.WidthMm, d.HeightMm, d.CurveRadiusMm, d.FoldDegrees })
                if (!double.IsFinite(v)) throw new ArgumentException("Panel values must be finite.");
            specs.Add(new DisplaySpec(d.Id, d.WidthPx, d.HeightPx, d.WidthMm, d.HeightMm,
                d.CurveRadiusMm, d.FoldDegrees));
            width = checked(width + d.WidthPx);
        }
        _ = checked(DesktopX + width);
        _ = checked(DesktopY + Displays[0].HeightPx);
        Starts.Validate();
        return new RigDefinition(specs, CenterIndex, EyeDistanceMm, EyeHeightMm, BezelGapMm);
    }

    public static TripleConfig Parse(ReadOnlySpan<byte> utf8)
    {
        if (utf8.Length is 0 or > 65536) throw new ArgumentException("Config must be 1-65536 UTF-8 bytes.");
        if (utf8.StartsWith(new byte[] { 0xEF, 0xBB, 0xBF })) utf8 = utf8[3..];
        using var document = JsonDocument.Parse(utf8.ToArray(), new JsonDocumentOptions { MaxDepth = 16 });
        CheckUnique(document.RootElement);
        var options = new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
            MaxDepth = 16
        };
        options.Converters.Add(new JsonStringEnumConverter(JsonNamingPolicy.CamelCase, allowIntegerValues: false));
        var config = document.RootElement.Deserialize<TripleConfig>(options)
            ?? throw new ArgumentException("Config must be an object.");
        _ = config.Rig();
        return config;
    }

    private static void CheckUnique(JsonElement node)
    {
        if (node.ValueKind == JsonValueKind.Object)
        {
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var p in node.EnumerateObject())
            {
                if (!seen.Add(p.Name)) throw new ArgumentException($"Duplicate config key: {p.Name}");
                CheckUnique(p.Value);
            }
        }
        else if (node.ValueKind == JsonValueKind.Array)
            foreach (var child in node.EnumerateArray()) CheckUnique(child);
    }
}
