import Foundation
import CoreGraphics

nonisolated(unsafe) var _writeFd: Int32 = -1
nonisolated(unsafe) var _isKeyDown = false
nonisolated(unsafe) var _eventTap: CFMachPort? = nil

func eventTapCallback(
    proxy: CGEventTapProxy,
    type: CGEventType,
    event: CGEvent,
    refcon: UnsafeMutableRawPointer?
) -> Unmanaged<CGEvent>? {
    if type == .tapDisabledByTimeout || type == .tapDisabledByUserInput {
        if let tap = _eventTap { CGEvent.tapEnable(tap: tap, enable: true) }
        return nil
    }

    let keyCode = event.getIntegerValueField(.keyboardEventKeycode)
    guard keyCode == 58 else { return Unmanaged.passRetained(event) } // left Option

    let fd = _writeFd
    guard fd >= 0 else { return Unmanaged.passRetained(event) }

    if type == .keyDown, !_isKeyDown {
        _isKeyDown = true
        var buf: [UInt8] = [68, 10] // "D\n"
        Darwin.write(fd, &buf, 2)
    } else if type == .keyUp, _isKeyDown {
        _isKeyDown = false
        var buf: [UInt8] = [85, 10] // "U\n"
        Darwin.write(fd, &buf, 2)
    }
    return Unmanaged.passRetained(event)
}

func main() {
    // Named FIFO for IPC — avoids posix_spawn FD inheritance issues entirely.
    let fifoPath = "/tmp/panda-hotkey-\(ProcessInfo.processInfo.processIdentifier).fifo"
    Darwin.mkfifo(fifoPath, 0o600)

    let projectDir = (Bundle.main.bundlePath as NSString).deletingLastPathComponent

    let process = Process()
    process.executableURL = URL(fileURLWithPath: "\(projectDir)/.venv/bin/python")
    process.arguments = ["\(projectDir)/launch.py"]
    process.currentDirectoryURL = URL(fileURLWithPath: projectDir)
    process.environment = ProcessInfo.processInfo.environment.merging([
        "PANDA_SWIFT_LAUNCHER": "1",
        "PANDA_HOTKEY_FIFO": fifoPath,
    ]) { _, new in new }

    do {
        try process.run()
    } catch {
        fputs("PandaVoice: failed to launch Python: \(error)\n", stderr)
        Darwin.unlink(fifoPath)
        exit(1)
    }

    Thread.detachNewThread {
        process.waitUntilExit()
        Darwin.unlink(fifoPath)
        CFRunLoopStop(CFRunLoopGetMain())
    }

    // Open FIFO write-end in background — blocks until Python opens the read-end.
    Thread.detachNewThread {
        let fd = Darwin.open(fifoPath, O_WRONLY)
        if fd < 0 {
            fputs("PandaVoice: failed to open FIFO for writing\n", stderr)
        } else {
            _writeFd = fd
        }
    }

    let eventMask: CGEventMask =
        (1 << CGEventType.keyDown.rawValue) | (1 << CGEventType.keyUp.rawValue)

    guard let tap = CGEvent.tapCreate(
        tap: .cgSessionEventTap,
        place: .headInsertEventTap,
        options: .defaultTap,
        eventsOfInterest: eventMask,
        callback: eventTapCallback,
        userInfo: nil
    ) else {
        fputs("PandaVoice: cannot create event tap — grant Accessibility to Panda Voice.app\n", stderr)
        process.terminate()
        exit(1)
    }

    _eventTap = tap
    let source = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, tap, 0)
    CFRunLoopAddSource(CFRunLoopGetMain(), source, .commonModes)
    CGEvent.tapEnable(tap: tap, enable: true)

    CFRunLoopRun()
}

main()
