import UIKit

enum ImageUtil {
    /// The library's input rule: page-shaped images go to the target size, crops stay as they are, all capped.
    static func targetSize(_ s: CGSize, megapixels: Double) -> CGSize {
        let w = Double(s.width), h = Double(s.height), target = megapixels * 1e6
        let pageShaped = max(w, h) / min(w, h) <= 2.0 && min(w, h) >= 450
        let k = (w * h > target || pageShaped) ? (target / (w * h)).squareRoot() : 1.0
        return CGSize(width: (w * k).rounded(), height: (h * k).rounded())
    }

    /// Upright RGB bytes (w*h*3) at the target size; the photo's orientation is applied while drawing.
    static func rgb(_ image: UIImage, megapixels: Double) -> (Data, Int, Int)? {
        let pixelSize = CGSize(width: image.size.width * image.scale, height: image.size.height * image.scale)
        let size = targetSize(pixelSize, megapixels: megapixels)
        let w = Int(size.width), h = Int(size.height)
        guard w > 0, h > 0 else { return nil }
        var rgba = [UInt8](repeating: 255, count: w * h * 4)
        let ok: Bool = rgba.withUnsafeMutableBytes { buf in
            guard let ctx = CGContext(data: buf.baseAddress, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4,
                                      space: CGColorSpaceCreateDeviceRGB(),
                                      bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { return false }
            ctx.setFillColor(UIColor.white.cgColor)
            ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
            UIGraphicsPushContext(ctx)
            ctx.translateBy(x: 0, y: CGFloat(h)); ctx.scaleBy(x: 1, y: -1)   // UIKit drawing is top-left based
            image.draw(in: CGRect(x: 0, y: 0, width: w, height: h))
            UIGraphicsPopContext()
            return true
        }
        guard ok else { return nil }
        var rgb = Data(count: w * h * 3)
        rgb.withUnsafeMutableBytes { (out: UnsafeMutableRawBufferPointer) in
            let o = out.bindMemory(to: UInt8.self)
            for i in 0..<(w * h) { o[3 * i] = rgba[4 * i]; o[3 * i + 1] = rgba[4 * i + 1]; o[3 * i + 2] = rgba[4 * i + 2] }
        }
        return (rgb, w, h)
    }
}
