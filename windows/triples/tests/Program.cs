using System.Text;
using System.Text.Json;
using Dbce.TripleScreen;
using Fh2.Triples;

int checks = 0;
void Check(bool condition, string reason)
{
    if (!condition) throw new Exception(reason);
    checks++;
}
void Near(double actual, double expected, string reason) =>
    Check(Math.Abs(actual - expected) <= 1e-9 * Math.Max(1, Math.Abs(expected)), reason);
void Refuses(Action action, string reason)
{
    try { action(); }
    catch (Exception e) when (e is ArgumentException or JsonException or OverflowException or InvalidOperationException)
    { checks++; return; }
    throw new Exception("Accepted invalid " + reason);
}
TripleConfig Rig(double radius = 0, double eye = 660, double left = 65, double right = 70) => new()
{
    SchemaVersion = 1, Enabled = true, CenterIndex = 1, EyeDistanceMm = eye, DesktopX = -2560,
    Displays = new[]
    {
        new PanelConfig("left", 2560, 1440, 697, 392, radius, left),
        new PanelConfig("center", 2560, 1440, 697, 392, radius),
        new PanelConfig("right", 2560, 1440, 697, 392, radius, right)
    }
};
FramePlan Plan(TripleConfig config, CameraState? state = null, CameraKind camera = CameraKind.Cockpit,
    double gameFov = 60) => ProjectionPlan.Build(config, state ?? new CameraState(config.Starts), camera, gameFov, 50, 1_000_000);
Vector3d Ray(PlannedView view, double u)
{
    view.Warp.SourceUv(u, .5, out double su, out double sv);
    var s = view.Warp.SourceSurface;
    return (s.LowerLeft + (s.LowerRight - s.LowerLeft) * su + (s.UpperLeft - s.LowerLeft) * sv).Normalized();
}
void Coverage(FramePlan frame)
{
    int x = 0;
    foreach (var v in frame.Views)
    {
        Check(v.Pixels.X == x && v.Pixels.Y == 0 && v.Pixels.Width > 0 &&
            v.Pixels.Height == frame.Window.Height, "one-window pixel coverage");
        x += v.Pixels.Width;
    }
    Check(x == frame.Window.Width, "complete span without duplicate windows");
}
void ProjectedCorner(OffAxisProjection p, Vector3d point, double expectedX, double expectedY)
{
    var d = point - p.CameraPosition;
    double[] v = { Vector3d.Dot(d, p.CameraRight), Vector3d.Dot(d, p.CameraUp),
        -Vector3d.Dot(d, p.CameraForward), 1 };
    double[] clip = new double[4];
    for (int r = 0; r < 4; r++)
        for (int c = 0; c < 4; c++) clip[r] += p.ProjectionMatrix[r, c] * v[c];
    Near(clip[0] / clip[3], expectedX, "actual projection corner X");
    Near(clip[1] / clip[3], expectedY, "actual projection corner Y");
}
void Seams(FramePlan frame)
{
    for (int i = 1; i < frame.Views.Count; i++)
    {
        var a = Ray(frame.Views[i - 1], 1);
        var b = Ray(frame.Views[i], 0);
        Near(a.X, b.X, "seam ray X"); Near(a.Y, b.Y, "seam ray Y"); Near(a.Z, b.Z, "seam ray Z");
    }
}

// Physical fixtures exercise the actual consumer and canonical toolkit, not a copied projection formula.
foreach (double radius in new[] { 0d, 1500d })
foreach (var angles in new[] { (0d, 0d), (65d, 70d), (70d, 65d) })
foreach (CameraKind camera in new[] { CameraKind.Cockpit, CameraKind.Bonnet })
{
    var config = Rig(radius, 660, angles.Item1, angles.Item2);
    var frame = Plan(config, camera: camera);
    Check(frame.Corrected && frame.Views.Count == 3, "three distinct flat/normal-curved views");
    Coverage(frame); Seams(frame);
    foreach (var view in frame.Views)
    {
        var p = view.Projection;
        ProjectedCorner(p, p.Surface.LowerLeft, -1, -1);
        ProjectedCorner(p, p.Surface.LowerRight, 1, -1);
        ProjectedCorner(p, p.Surface.UpperLeft, -1, 1);
        var m = p.ProjectionMatrix;
        Near((m[2, 2] * -p.Near + m[2, 3]) / p.Near, -1, "near clip depth");
        Near((m[2, 2] * -p.Far + m[2, 3]) / p.Far, 1, "far clip depth");
    }
}
var curved = Rig(1500);
var seat = Plan(curved);
Near(seat.EffectiveEyeDistanceMm, 660, "edge-plane distance without sagitta subtraction");
Near(RigPlanner.Surfaces(curved.Rig())[1].Center.Z, -660, "canonical edge plane");
Check(seat.Views[0].Projection.CameraForward.X < 0 && seat.Views[2].Projection.CameraForward.X > 0,
    "side views face distinct directions");
Check(Math.Abs(seat.Views[0].Projection.CameraForward.X) != Math.Abs(seat.Views[2].Projection.CameraForward.X),
    "independent left/right folds");
var game = Plan(curved, camera: CameraKind.Bonnet);
Check(game.Set == FramingSet.Game && game.EffectiveEyeDistanceMm < 660, "game framing uses virtual eye");
var physical = RigPlanner.Plan(curved.Rig());
for (int i = 0; i < physical.Count; i++)
{
    foreach (double u in new[] { 0d, .25, .5, .75, 1d })
    {
        physical[i].Warp.SourceUv(u, .3, out double pu, out double pv);
        game.Views[i].Warp.SourceUv(u, .3, out double gu, out double gv);
        Near(pu, gu, "Game warp measured-eye U"); Near(pv, gv, "Game warp measured-eye V");
    }
}
var wrongVirtual = CurvedPanelWarp.Create(game.Views[1].Warp.SourceSurface, new Vector3d(0, 0, 0), 1500);
wrongVirtual.SourceUv(.25, .3, out double wrongU, out _);
game.Views[1].Warp.SourceUv(.25, .3, out double correctU, out _);
Check(Math.Abs(wrongU - correctU) > 1e-4, "negative control: virtual-eye warp differs");

// Canonical planner slices a close curved display; pixels still cover the one window exactly.
var sliced = Plan(Rig(1500, 100));
Check(sliced.Views.Count > 3, "curve slice plan retained"); Coverage(sliced); Seams(sliced);
var uneven = Rig() with { Displays = new[]
{
    new PanelConfig("left",1920,1440,610,392,0,60),
    new PanelConfig("center",2560,1440,697,392),
    new PanelConfig("right",1600,1440,500,392,0,70)
}};
var unevenPlan = Plan(uneven); Coverage(unevenPlan); Seams(unevenPlan);
Check(unevenPlan.Window.Width == 6080 && unevenPlan.Window.X == -2560, "unequal widths/negative origin");
var five = Rig() with { CenterIndex = 2, Displays = Enumerable.Range(0, 5)
    .Select(i => new PanelConfig(i.ToString(), 1920, 1080, 600, 338, 0, i == 2 ? 0 : 15)).ToArray() };
Check(Plan(five).Views.Count == 5, "RigDefinition supports more than three displays");
Coverage(Plan(five)); Seams(Plan(five));
Check(!Plan(Rig() with { Enabled = false }).Corrected, "disabled passthrough");
Check(Plan(Rig() with { CenterIndex = 0, Displays = new[] { Rig().Displays[1] } }).Views.Count == 0,
    "single screen keeps game behavior");

var state = new CameraState(new CameraStarts());
Check(state.Selected(CameraKind.Cockpit) == FramingSet.Realistic && state.Selected(CameraKind.Bumper) == FramingSet.Realistic,
    "mounted Realistic starts");
Check(state.Selected(CameraKind.Bonnet) == FramingSet.Game && state.Selected(CameraKind.Chase) == FramingSet.Game,
    "bonnet/chase Game starts");
state.SetOffset(CameraKind.Cockpit, FramingSet.Realistic, 4);
var narrow = Plan(curved, state).EffectiveEyeDistanceMm;
Check(narrow < 660, "wider Realistic offset uses closer virtual eye");
state.Toggle(CameraKind.Cockpit);
state.SetOffset(CameraKind.Cockpit, FramingSet.Game, -2);
state.Toggle(CameraKind.Bonnet);
Check(state.Selected(CameraKind.Cockpit) == FramingSet.Game && state.Selected(CameraKind.Bonnet) == FramingSet.Realistic,
    "independent camera choices");
state.Toggle(CameraKind.Cockpit);
Near(state.Offset(CameraKind.Cockpit, FramingSet.Realistic), 4, "independent saved set offset");
state.ResetOffset(CameraKind.Cockpit);
Near(Plan(curved, state).EffectiveEyeDistanceMm, 660, "reset to calculated start");
Near(state.Offset(CameraKind.Cockpit, FramingSet.Game), -2, "reset leaves other set alone");

// Strict raw-config boundary: no reader/writer touches an owner file.
string json = """
{"schemaVersion":1,"enabled":true,"centerIndex":1,"eyeDistanceMm":660,"displays":[
 {"id":"left","widthPx":2560,"heightPx":1440,"widthMm":697,"heightMm":392,"foldDegrees":65},
 {"id":"center","widthPx":2560,"heightPx":1440,"widthMm":697,"heightMm":392},
 {"id":"right","widthPx":2560,"heightPx":1440,"widthMm":697,"heightMm":392,"foldDegrees":70}]}
""";
TripleConfig Parse(string value) => TripleConfig.Parse(Encoding.UTF8.GetBytes(value));
Check(Plan(Parse(json)).Views.Count == 3, "strict config feeds actual planner");
var example = TripleConfig.Parse(File.ReadAllBytes(Path.Combine(AppContext.BaseDirectory, "three-flat.json")));
Check(Plan(example).Views.Count == 3 && Plan(example).Window.Width == 7680, "checked-in config feeds actual planner");
var bom = new byte[] { 0xEF, 0xBB, 0xBF }.Concat(Encoding.UTF8.GetBytes(json)).ToArray();
Check(Plan(TripleConfig.Parse(bom)).Views.Count == 3 && bom[0] == 0xEF, "BOM read without mutating input");
var customStart = Parse(json.Replace("\"enabled\":true", "\"enabled\":true,\"starts\":{\"cockpit\":\"game\"}"));
var customState = new CameraState(customStart.Starts);
Check(customState.Selected(CameraKind.Cockpit) == FramingSet.Game &&
    customState.Selected(CameraKind.Bumper) == FramingSet.Realistic, "explicit start affects only its camera");
foreach (string bad in new[] { json.Replace("\"schemaVersion\":1", "\"schemaVersion\":2"),
    json.Replace("\"enabled\":true", "\"enabled\":true,\"extra\":0"),
    json.Replace("\"enabled\":true", "\"enabled\":true,\"enabled\":false"),
    json.Replace("\"eyeDistanceMm\":660,", ""), json.Replace("660", "\"660\""),
    json.Replace("\"center\"", "\"left\""), json.Replace("1440", "0"),
    json.Replace("\"foldDegrees\":65", "\"foldDegrees\":null"),
    json.Replace("\"enabled\":true", "\"enabled\":true,\"starts\":{\"cockpit\":12}"),
    json.Replace("\"enabled\":true", "\"enabled\":true,\"starts\":null"), json + "garbage", "null" })
    Refuses(() => Parse(bad), "JSON fixture");
Refuses(() => TripleConfig.Parse(new byte[] { 255, 254 }), "UTF8");
Refuses(() => TripleConfig.Parse(new byte[65537]), "oversized input");
Refuses(() => Plan(Rig() with { EyeDistanceMm = double.NaN }), "NaN eye");
Refuses(() => Plan(Rig(double.PositiveInfinity)), "infinite radius");
Refuses(() => Plan(Rig() with { DesktopX = int.MaxValue }), "pixel overflow");
Refuses(() => Plan(Rig(), gameFov: double.NaN), "NaN FOV");
Refuses(() => ProjectionPlan.Build(Rig(), state, CameraKind.Cockpit, 60, 50, 10), "clip range");
state.SetOffset(CameraKind.Cockpit, FramingSet.Realistic, 300);
Refuses(() => Plan(Rig(), state), "impossible offset without clamping");

// Guest camera convention adapter: actual physical off-axis corners, not a second copied frustum formula.
void GuestNear(double actual, double expected, string reason) =>
    Check(Math.Abs(actual - expected) <= 3e-6 * Math.Max(1, Math.Abs(expected)), reason);
double[] GuestClip(float[] matrix, double x, double y, double z)
{
    double[] point = { x, y, z, 1 }, clip = new double[4];
    for (int c = 0; c < 4; c++)
        for (int r = 0; r < 4; r++) clip[c] += point[r] * matrix[r * 4 + c];
    return clip;
}
foreach (var config in new[] { Rig(), Rig(1500), Rig(left: 40, right: 75) })
foreach (var view in Plan(config).Views)
foreach (GuestForwardAxis axis in Enum.GetValues<GuestForwardAxis>())
foreach (bool negate in new[] { false, true })
{
    var p = view.Projection;
    var matrix = GuestProjection.EncodeForMetres(p, axis, negate);
    double forward = axis == GuestForwardAxis.PositiveZ ? 1 : -1, xy = negate ? -1 : 1;
    foreach (var (corner, ex, ey) in new[] { (p.Surface.LowerLeft, -1d, -1d),
                 (p.Surface.LowerRight, 1d, -1d), (p.Surface.UpperLeft, -1d, 1d) })
    {
        var d = corner - p.CameraPosition;
        var clip = GuestClip(matrix, Vector3d.Dot(d, p.CameraRight) / 1000,
            Vector3d.Dot(d, p.CameraUp) / 1000, forward * Vector3d.Dot(d, p.CameraForward) / 1000);
        GuestNear(clip[0] / clip[3], xy * ex, "guest row-vector off-axis corner X");
        GuestNear(clip[1] / clip[3], xy * ey, "guest row-vector off-axis corner Y");
    }
    var near = GuestClip(matrix, 0, 0, forward * p.Near / 1000);
    var far = GuestClip(matrix, 0, 0, forward * p.Far / 1000);
    GuestNear(near[2] / near[3], 1, "guest near depth1");
    GuestNear(far[2] / far[3], 0, "guest far depth0");
}
var flatProjection = Plan(Rig()).Views[1].Projection;
Refuses(() => GuestProjection.EncodeForMetres(flatProjection, (GuestForwardAxis)99, false), "guest forward axis");
Refuses(() => GuestProjection.EncodeForMetres(null!, GuestForwardAxis.NegativeZ, false), "null projection");
var enormousClips = ProjectionCalculator.Calculate(flatProjection.Surface, new Vector3d(0, 0, 0), 1e45, 2e45);
Refuses(() => GuestProjection.EncodeForMetres(enormousClips, GuestForwardAxis.NegativeZ, false), "guest float overflow");
var controlMatrix = GuestProjection.EncodeForMetres(flatProjection, GuestForwardAxis.NegativeZ, false);
var wrongUnits = (float[])controlMatrix.Clone(); wrongUnits[14] *= 1000;
var wrongTranspose = new float[16];
for (int r = 0; r < 4; r++) for (int c = 0; c < 4; c++) wrongTranspose[r * 4 + c] = controlMatrix[c * 4 + r];
foreach (var wrong in new[] { wrongUnits, wrongTranspose,
             GuestProjection.EncodeForMetres(flatProjection, GuestForwardAxis.PositiveZ, false) })
{
    var clip = GuestClip(wrong, 0, 0, -flatProjection.Near / 1000);
    Check(Math.Abs(clip[2] / clip[3] - 1) > .1, "negative control catches wrong units/transpose/forward axis");
}

if (args.Length == 2 && args[0] == "--guest-oracle")
{
    using var oracle = JsonDocument.Parse(File.ReadAllBytes(args[1]));
    Check(oracle.RootElement.GetProperty("imageSha256").GetString() ==
        "3708A857A4EEC4BC673DF3CD0F00D304702E67B7A5570B9D34C1803CA2102244", "oracle title image identity");
    var cases = oracle.RootElement.GetProperty("cases");
    Check(cases.GetArrayLength() == 288, "all actual generated matrix cases present");
    foreach (var sample in cases.EnumerateArray())
    {
        double fov = sample.GetProperty("fovDegrees").GetDouble(), aspect = sample.GetProperty("aspect").GetDouble();
        double height = 2000 * Math.Tan(fov * Math.PI / 360), width = height * aspect;
        var screen = new DisplaySurface("stock-oracle", new Vector3d(-width / 2, -height / 2, -1000),
            new Vector3d(width / 2, -height / 2, -1000), new Vector3d(-width / 2, height / 2, -1000));
        var projection = ProjectionCalculator.Calculate(screen, new Vector3d(0, 0, 0),
            sample.GetProperty("nearMetres").GetDouble() * 1000, sample.GetProperty("farMetres").GetDouble() * 1000);
        var axis = sample.GetProperty("mode").GetInt32() == 0 ? GuestForwardAxis.PositiveZ : GuestForwardAxis.NegativeZ;
        var matrix = GuestProjection.EncodeForMetres(projection, axis, sample.GetProperty("negateClipXY").GetBoolean());
        var stock = sample.GetProperty("matrix");
        Check(stock.GetArrayLength() == 16, "actual stock matrix length");
        for (int i = 0; i < 16; i++) GuestNear(matrix[i], stock[i].GetDouble(), "adapter vs actual generated projection");
    }
}
else if (args.Length != 0) throw new ArgumentException("Use --guest-oracle <private oracle.json> or no arguments.");
Console.WriteLine($"PASS: {checks} checks; canonical RigDefinition/RigPlanner consumer; no game/device/window/file writes");
