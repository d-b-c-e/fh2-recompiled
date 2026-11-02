namespace Fh2.Triples;

public enum CameraKind { Cockpit, Bonnet, Bumper, Chase, Other }
public enum FramingSet { Game, Realistic }

public sealed record CameraStarts
{
    public FramingSet Cockpit { get; init; } = FramingSet.Realistic;
    public FramingSet Bonnet { get; init; } = FramingSet.Game;
    public FramingSet Bumper { get; init; } = FramingSet.Realistic;
    public FramingSet Chase { get; init; } = FramingSet.Game;

    internal void Validate()
    {
        foreach (var s in new[] { Cockpit, Bonnet, Bumper, Chase })
            if (!Enum.IsDefined(s)) throw new ArgumentException("Unknown camera starting set.");
    }

    public FramingSet For(CameraKind camera) => camera switch
    {
        CameraKind.Cockpit => Cockpit, CameraKind.Bonnet => Bonnet,
        CameraKind.Bumper => Bumper, CameraKind.Chase => Chase, _ => FramingSet.Game
    };
}

// Offline camera policy; no native camera detection, hotkey or persistence is claimed.
public sealed class CameraState
{
    private readonly Dictionary<CameraKind, FramingSet> _selected = new();
    private readonly Dictionary<(CameraKind, FramingSet), double> _offsets = new();
    private readonly CameraStarts _starts;

    public CameraState(CameraStarts starts) { starts.Validate(); _starts = starts; }
    public FramingSet Selected(CameraKind camera) => _selected.GetValueOrDefault(camera, _starts.For(camera));
    public void Toggle(CameraKind camera) => _selected[camera] = Selected(camera) == FramingSet.Game
        ? FramingSet.Realistic : FramingSet.Game;
    public double Offset(CameraKind camera, FramingSet set) => _offsets.GetValueOrDefault((camera, set));
    public void SetOffset(CameraKind camera, FramingSet set, double degrees)
    {
        if (!double.IsFinite(degrees)) throw new ArgumentException("FOV offset must be finite.");
        _offsets[(camera, set)] = degrees;
    }
    public void ResetOffset(CameraKind camera) => _offsets.Remove((camera, Selected(camera)));
}
