using Dbce.TripleScreen;

namespace Fh2.Triples;

public enum GuestForwardAxis { PositiveZ, NegativeZ }

// Offline conversion for metre-coordinate consumers; runtime units/mode/flags must be identified by the caller.
public static class GuestProjection
{
    public static float[] EncodeForMetres(OffAxisProjection projection, GuestForwardAxis forwardAxis, bool negateClipXY)
    {
        ArgumentNullException.ThrowIfNull(projection);
        if (!Enum.IsDefined(forwardAxis)) throw new ArgumentException("Unknown guest forward axis.");
        var p = projection.ProjectionMatrix;
        if (p.ToRowMajorArray().Any(v => !double.IsFinite(v)) ||
            !double.IsFinite(projection.Near) || !double.IsFinite(projection.Far) ||
            projection.Near <= 0 || projection.Far <= projection.Near)
            throw new ArgumentException("Require a finite canonical perspective.");
        double forward = forwardAxis == GuestForwardAxis.PositiveZ ? 1 : -1;
        double xy = negateClipXY ? -1 : 1;
        // Reversed depth from near/far directly avoids subtracting almost-equal matrix coefficients.
        double a = projection.Near / (projection.Far - projection.Near);
        double b = a * projection.Far / 1000; // mm -> metres; perspective scales stay dimensionless.
        double[] rowMajor = {
            xy * p[0, 0], 0, 0, 0,
            0, xy * p[1, 1], 0, 0,
            -forward * xy * p[0, 2], -forward * xy * p[1, 2], -forward * a, forward,
            0, 0, b, 0
        };
        var result = rowMajor.Select(v => (float)v).ToArray();
        if (result.Any(v => !float.IsFinite(v))) throw new ArgumentException("Guest float projection overflow.");
        return result;
    }
}
