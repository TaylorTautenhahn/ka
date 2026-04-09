import ApplicationServices
import CoreGraphics
import Foundation

enum MouseError: Error {
    case invalidArguments(String)
    case eventCreationFailed(String)
}

struct WindowSummary: Codable {
    let ownerName: String
    let windowName: String
    let layer: Int
    let x: Double
    let y: Double
    let width: Double
    let height: Double
}

func fromTopLeft(_ x: Double, _ y: Double) -> CGPoint {
    CGPoint(x: x, y: y)
}

func currentCursorTopLeft() -> CGPoint {
    let current = CGEvent(source: nil)?.location ?? .zero
    return CGPoint(x: current.x, y: current.y)
}

@discardableResult
func postMouseEvent(type: CGEventType, point: CGPoint, button: CGMouseButton = .left) throws -> Bool {
    guard let event = CGEvent(mouseEventSource: nil, mouseType: type, mouseCursorPosition: point, mouseButton: button) else {
        throw MouseError.eventCreationFailed("Failed to create \(type) event.")
    }

    event.post(tap: .cghidEventTap)
    return true
}

func move(to point: CGPoint) throws {
    _ = try postMouseEvent(type: .mouseMoved, point: point)
}

func click(at point: CGPoint) throws {
    try move(to: point)
    usleep(25_000)
    _ = try postMouseEvent(type: .leftMouseDown, point: point)
    usleep(25_000)
    _ = try postMouseEvent(type: .leftMouseUp, point: point)
}

func drag(from start: CGPoint, to end: CGPoint, durationMs: Int) throws {
    let clampedDuration = max(durationMs, 60)
    let steps = max(12, clampedDuration / 12)
    let sleepMicros = useconds_t((clampedDuration * 1000) / steps)

    try move(to: start)
    usleep(120_000)
    _ = try postMouseEvent(type: .leftMouseDown, point: start)
    usleep(180_000)

    // A tiny initial nudge helps some apps recognize the gesture as a drag.
    let nudge = CGPoint(x: start.x + 1.0, y: start.y + 1.0)
    _ = try postMouseEvent(type: .leftMouseDragged, point: nudge)
    usleep(35_000)

    for step in 1...steps {
        let fraction = CGFloat(step) / CGFloat(steps)
        let point = CGPoint(
            x: start.x + ((end.x - start.x) * fraction),
            y: start.y + ((end.y - start.y) * fraction)
        )
        _ = try postMouseEvent(type: .leftMouseDragged, point: point)
        usleep(sleepMicros)
    }

    // Mirroring is more reliable if we briefly dwell on the target before release.
    usleep(220_000)
    _ = try postMouseEvent(type: .leftMouseUp, point: end)
    usleep(60_000)
}

func mouseDown(at point: CGPoint) throws {
    try move(to: point)
    usleep(25_000)
    _ = try postMouseEvent(type: .leftMouseDown, point: point)
}

func mouseUp(at point: CGPoint? = nil) throws {
    let finalPoint = point ?? (CGEvent(source: nil)?.location ?? .zero)
    _ = try postMouseEvent(type: .leftMouseUp, point: finalPoint)
}

func dragTo(_ end: CGPoint, durationMs: Int) throws {
    let start = CGEvent(source: nil)?.location ?? .zero
    let clampedDuration = max(durationMs, 60)
    let steps = max(12, clampedDuration / 12)
    let sleepMicros = useconds_t((clampedDuration * 1000) / steps)

    for step in 1...steps {
        let fraction = CGFloat(step) / CGFloat(steps)
        let point = CGPoint(
            x: start.x + ((end.x - start.x) * fraction),
            y: start.y + ((end.y - start.y) * fraction)
        )
        _ = try postMouseEvent(type: .leftMouseDragged, point: point)
        usleep(sleepMicros)
    }
}

func usage() {
    let lines = [
        "Usage:",
        "  block_blast_mouse position",
        "  block_blast_mouse click <x> <y>",
        "  block_blast_mouse drag <x1> <y1> <x2> <y2> [duration_ms]",
        "  block_blast_mouse down <x> <y>",
        "  block_blast_mouse dragto <x> <y> [duration_ms]",
        "  block_blast_mouse up [x y]",
        "  block_blast_mouse capture <x> <y> <width> <height> <path>",
        "  block_blast_mouse windows"
    ]
    FileHandle.standardError.write(lines.joined(separator: "\n").data(using: .utf8)!)
}

func capture(region: CGRect, to path: String) throws {
    let task = Process()
    task.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
    task.arguments = [
        "-x",
        "-R",
        "\(Int(region.origin.x.rounded())),\(Int(region.origin.y.rounded())),\(Int(region.width.rounded())),\(Int(region.height.rounded()))",
        path
    ]
    try task.run()
    task.waitUntilExit()
    if task.terminationStatus != 0 {
        throw MouseError.eventCreationFailed("screencapture failed with status \(task.terminationStatus).")
    }
}

do {
    let args = Array(CommandLine.arguments.dropFirst())
    guard let command = args.first else {
        usage()
        throw MouseError.invalidArguments("Missing command.")
    }

    switch command {
    case "position":
        let point = currentCursorTopLeft()
        print("\(Int(point.x.rounded())) \(Int(point.y.rounded()))")
    case "click":
        guard args.count == 3, let x = Double(args[1]), let y = Double(args[2]) else {
            usage()
            throw MouseError.invalidArguments("click expects <x> <y>.")
        }
        try click(at: fromTopLeft(x, y))
    case "drag":
        guard args.count == 5 || args.count == 6 else {
            usage()
            throw MouseError.invalidArguments("drag expects <x1> <y1> <x2> <y2> [duration_ms].")
        }
        guard
            let x1 = Double(args[1]),
            let y1 = Double(args[2]),
            let x2 = Double(args[3]),
            let y2 = Double(args[4])
        else {
            usage()
            throw MouseError.invalidArguments("drag coordinates must be numeric.")
        }
        let durationMs = args.count == 6 ? (Int(args[5]) ?? 250) : 250
        try drag(from: fromTopLeft(x1, y1), to: fromTopLeft(x2, y2), durationMs: durationMs)
    case "down":
        guard args.count == 3, let x = Double(args[1]), let y = Double(args[2]) else {
            usage()
            throw MouseError.invalidArguments("down expects <x> <y>.")
        }
        try mouseDown(at: fromTopLeft(x, y))
    case "dragto":
        guard args.count == 3 || args.count == 4 else {
            usage()
            throw MouseError.invalidArguments("dragto expects <x> <y> [duration_ms].")
        }
        guard let x = Double(args[1]), let y = Double(args[2]) else {
            usage()
            throw MouseError.invalidArguments("dragto coordinates must be numeric.")
        }
        let durationMs = args.count == 4 ? (Int(args[3]) ?? 250) : 250
        try dragTo(fromTopLeft(x, y), durationMs: durationMs)
    case "up":
        if args.count == 1 {
            try mouseUp()
        } else if args.count == 3, let x = Double(args[1]), let y = Double(args[2]) {
            try mouseUp(at: fromTopLeft(x, y))
        } else {
            usage()
            throw MouseError.invalidArguments("up expects no args or <x> <y>.")
        }
    case "windows":
        let options: CGWindowListOption = [.optionOnScreenOnly, .excludeDesktopElements]
        guard let infoList = CGWindowListCopyWindowInfo(options, kCGNullWindowID) as? [[String: Any]] else {
            throw MouseError.eventCreationFailed("Failed to query window list.")
        }
        let windows: [WindowSummary] = infoList.compactMap { info in
            guard
                let ownerName = info[kCGWindowOwnerName as String] as? String,
                let boundsDict = info[kCGWindowBounds as String] as? [String: Any],
                let x = boundsDict["X"] as? Double,
                let y = boundsDict["Y"] as? Double,
                let width = boundsDict["Width"] as? Double,
                let height = boundsDict["Height"] as? Double
            else {
                return nil
            }
            let windowName = info[kCGWindowName as String] as? String ?? ""
            let layer = info[kCGWindowLayer as String] as? Int ?? 0
            return WindowSummary(
                ownerName: ownerName,
                windowName: windowName,
                layer: layer,
                x: x,
                y: y,
                width: width,
                height: height
            )
        }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(windows)
        FileHandle.standardOutput.write(data)
    case "capture":
        guard args.count == 6,
              let x = Double(args[1]),
              let y = Double(args[2]),
              let width = Double(args[3]),
              let height = Double(args[4]) else {
            usage()
            throw MouseError.invalidArguments("capture expects <x> <y> <width> <height> <path>.")
        }
        try capture(region: CGRect(x: x, y: y, width: width, height: height), to: args[5])
    default:
        usage()
        throw MouseError.invalidArguments("Unknown command \(command).")
    }
} catch {
    FileHandle.standardError.write("block_blast_mouse error: \(error)\n".data(using: .utf8)!)
    exit(1)
}
