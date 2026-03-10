#!/usr/bin/env python3
"""
Capture an animated HTML diagram as MP4 and GIF.
Controls the browser animation clock for frame-perfect timing.

Usage:
  python capture.py input.html [--duration 8] [--fps 30] [--format both]
"""

import argparse, asyncio, os, shutil, subprocess, sys
from pathlib import Path


def _find_ffmpeg():
    """Find a full ffmpeg binary with H.264 support.

    Search order:
      1. 'ffmpeg' in PATH
      2. imageio_ffmpeg pip package (ships a full static build)
      3. ~/.local/bin/ffmpeg symlink
    Returns the path string or raises FileNotFoundError.
    """
    # 1. Check PATH
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    # 2. imageio_ffmpeg pip package
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.isfile(path):
            return path
    except ImportError:
        pass
    # 3. ~/.local/bin fallback
    local = os.path.expanduser("~/.local/bin/ffmpeg")
    if os.path.isfile(local):
        return local
    raise FileNotFoundError(
        "ffmpeg not found. Install via: pip install imageio-ffmpeg\n"
        "Or: brew install ffmpeg"
    )


FFMPEG = _find_ffmpeg()

PAUSE_AND_STEP_JS = """
(() => {
  const anims = document.getAnimations();
  anims.forEach(a => a.pause());
  window.__setTime = (ms) => {
    const anims = document.getAnimations();
    anims.forEach(a => {
      if (a.effect && a.effect.getTiming) {
        const t = a.effect.getTiming();
        const dur = t.duration || 1000;
        const del = t.delay || 0;
        if (t.iterations === Infinity) {
          const local = ms - del;
          a.currentTime = local >= 0 ? del + (local % dur) : 0;
        } else {
          a.currentTime = Math.min(ms, (dur + del) * (t.iterations || 1));
        }
      }
    });
  };
})();
"""

async def capture_frames(html_path, frames_dir, duration, fps):
    from playwright.async_api import async_playwright
    frame_count = int(duration * fps)
    ms_per_frame = 1000.0 / fps
    url = f"file://{os.path.abspath(html_path)}"
    print(f"Capturing {frame_count} frames at {fps} FPS ({duration}s, {ms_per_frame:.1f}ms/frame)...")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        await page.goto(url)
        await page.wait_for_timeout(2000)
        await page.evaluate(PAUSE_AND_STEP_JS)
        await page.wait_for_timeout(100)

        for i in range(frame_count):
            await page.evaluate(f"window.__setTime({i * ms_per_frame})")
            await page.wait_for_timeout(10)
            await page.screenshot(
                path=os.path.join(frames_dir, f"frame_{i:04d}.png"),
                clip={"x": 0, "y": 0, "width": 1280, "height": 720}
            )
            if (i + 1) % fps == 0:
                print(f"  {(i+1)//fps}s / {int(duration)}s")

        await browser.close()
    print(f"All {frame_count} frames captured.")

def frames_to_mp4(frames_dir, output_path, fps):
    print(f"Encoding MP4 → {output_path}")
    subprocess.run([
        FFMPEG, "-y", "-framerate", str(fps),
        "-i", os.path.join(frames_dir, "frame_%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "18", "-preset", "slow", "-movflags", "+faststart",
        output_path
    ], check=True, capture_output=True)
    print(f"  ✓ MP4: {os.path.getsize(output_path)/1048576:.1f} MB")

def frames_to_gif(frames_dir, output_path, fps):
    print(f"Encoding GIF → {output_path}")
    gif_fps = min(fps, 15)
    pal = os.path.join(frames_dir, "palette.png")
    inp = os.path.join(frames_dir, "frame_%04d.png")
    subprocess.run([FFMPEG,"-y","-framerate",str(fps),"-i",inp,"-vf",
        f"fps={gif_fps},scale=1280:-1:flags=lanczos,palettegen=max_colors=128",
        pal], check=True, capture_output=True)
    subprocess.run([FFMPEG,"-y","-framerate",str(fps),"-i",inp,"-i",pal,
        "-lavfi",f"fps={gif_fps},scale=1280:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=3",
        "-loop","0",output_path], check=True, capture_output=True)
    print(f"  ✓ GIF: {os.path.getsize(output_path)/1048576:.1f} MB")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("html")
    parser.add_argument("--duration", type=float, default=8)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--format", choices=["mp4","gif","both"], default="both")
    args = parser.parse_args()

    stem = Path(args.html).stem
    out = os.path.dirname(os.path.abspath(args.html)) or "."
    fd = os.path.join(out, f".frames_{stem}")
    if os.path.exists(fd): shutil.rmtree(fd)
    os.makedirs(fd)

    try:
        await capture_frames(args.html, fd, args.duration, args.fps)
        if args.format in ("mp4","both"):
            frames_to_mp4(fd, os.path.join(out, f"{stem}.mp4"), args.fps)
        if args.format in ("gif","both"):
            frames_to_gif(fd, os.path.join(out, f"{stem}.gif"), args.fps)
        print("\nDone!")
    finally:
        shutil.rmtree(fd, ignore_errors=True)

if __name__ == "__main__":
    asyncio.run(main())
