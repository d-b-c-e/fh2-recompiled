using Dbce.TripleScreen;

namespace Fh2.Triples;

public sealed record WindowRect(int X, int Y, int Width, int Height);
public sealed record PlannedView(int DisplayIndex, int SliceIndex, PixelRect Pixels,
    OffAxisProjection Projection, CurvedPanelWarp Warp);
public sealed record FramePlan(bool Corrected, WindowRect Window, FramingSet Set,
    double EffectiveEyeDistanceMm, IReadOnlyList<PlannedView> Views);

public static class ProjectionPlan
{
    // RH +X right/+Y up, display towards -Z; M*v, row-major, depth[-1,1].
    // Near/far use mm here. Native guest units/clip conversion is not admitted yet.
    public static FramePlan Build(TripleConfig config, CameraState cameras, CameraKind camera,
        double gameVerticalFovDegrees, double nearMm, double farMm)
    {
        var rig = config.Rig();
        if (!double.IsFinite(gameVerticalFovDegrees) || gameVerticalFovDegrees is <= 0 or >= 180 ||
            !double.IsFinite(nearMm) || !double.IsFinite(farMm) || nearMm <= 0 || farMm <= nearMm)
            throw new ArgumentException("Require finite FOV in (0,180) and 0 < near < far.");
        int width = checked(config.Displays.Sum(d => d.WidthPx));
        var window = new WindowRect(config.DesktopX, config.DesktopY, width, config.Displays[0].HeightPx);
        if (!config.Enabled || config.Displays.Length == 1)
            return new FramePlan(false, window, FramingSet.Game, rig.EyeDistanceMm, Array.Empty<PlannedView>());

        var set = cameras.Selected(camera);
        double seatFov = 2 * Math.Atan(config.Displays[config.CenterIndex].HeightMm /
            (2 * rig.EyeDistanceMm)) * 180 / Math.PI;
        double fov = (set == FramingSet.Game ? gameVerticalFovDegrees : seatFov) + cameras.Offset(camera, set);
        if (!double.IsFinite(fov) || fov is <= 0 or >= 180)
            throw new ArgumentException("The selected offset produces an invalid FOV.");
        double distance = set == FramingSet.Realistic && cameras.Offset(camera, set) == 0
            ? rig.EyeDistanceMm
            : TripleRigDefinition.EyeDistanceForVerticalFov(config.Displays[config.CenterIndex].HeightMm, fov);

        var physical = RigPlanner.Plan(rig);
        var views = new List<PlannedView>(physical.Count);
        // Translate existing slices, retaining the measured-eye warp and slice identities.
        var shift = new Vector3d(0, 0, rig.EyeDistanceMm - distance);
        foreach (var slice in physical)
        {
            var p = slice.Panel;
            var source = new DisplaySurface(p.Id, p.LowerLeft + shift, p.LowerRight + shift, p.UpperLeft + shift);
            var warp = slice.Warp.WithSourceOn(source);
            var projection = ProjectionCalculator.Calculate(warp.SourceSurface, new Vector3d(0, 0, 0), nearMm, farMm);
            foreach (double v in projection.ProjectionMatrix.ToRowMajorArray())
                if (!double.IsFinite(v)) throw new ArgumentException("Nonfinite planned projection.");
            views.Add(new PlannedView(slice.DisplayIndex, slice.SliceIndex, slice.Pixels, projection, warp));
        }
        return new FramePlan(true, window, set, distance, views);
    }
}
