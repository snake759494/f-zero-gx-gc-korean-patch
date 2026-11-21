"""Background Dolphin controller.
python emu.py start <iso>     -> launches dsu server + dolphin (window parked off-screen, no focus)
python emu.py do "<cmds;...>" -> send pad commands (see dsu.py), ';' separated
python emu.py shot <name>     -> screenshot to shots/<name>.png
python emu.py stop
"""
import sys, os, subprocess, time, socket, glob, shutil, ctypes
from ctypes import wintypes

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOL = os.environ.get('DOLPHIN', 'Dolphin.exe')
USER = W + '/dolphin_user'
SHOTS = W + '/shots'
user32 = ctypes.windll.user32


def send(cmds):
    s = socket.create_connection(('127.0.0.1', 26761))
    f = s.makefile('rw')
    out = []
    for c in cmds:
        f.write(c + '\n'); f.flush(); out.append(f.readline().strip())
    s.close()
    return out


def dolphin_windows():
    pids = set()
    import psutil
    for p in psutil.process_iter(['name']):
        if (p.info['name'] or '').lower() == 'dolphin.exe': pids.add(p.pid)
    res = []
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, l):
        pid = wintypes.DWORD(); user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(h): res.append(h)
        return True
    user32.EnumWindows(cb, 0)
    return res


def park():
    for h in dolphin_windows():
        if user32.IsIconic(h): user32.ShowWindow(h, 4)
        # off-screen, bottom of z-order, never activate
        user32.SetWindowPos(h, 1, -4000, 100, 660, 520, 0x0010 | 0x0200)


def start(iso):
    os.makedirs(SHOTS, exist_ok=True)
    try:
        send(['clients'])
    except OSError:
        subprocess.Popen([sys.executable, W + '/tools/dsu.py'], creationflags=0x08000008, stdin=subprocess.DEVNULL, stdout=open(W + '/dsu.log', 'a'), stderr=subprocess.STDOUT, close_fds=True)
        time.sleep(1)
    si = subprocess.STARTUPINFO(); si.dwFlags = 1; si.wShowWindow = 4  # SW_SHOWNOACTIVATE
    subprocess.Popen([DOL, '-u', USER, '-b', '-e', iso], startupinfo=si, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True, creationflags=0x00000008)
    for _ in range(60):
        time.sleep(0.25)
        if dolphin_windows(): park()
    park()


def shot(name):
    before = set(glob.glob(USER + '/ScreenShots/**/*.png', recursive=True))
    send(['press SHOT 150'])
    for _ in range(40):
        time.sleep(0.25)
        now = set(glob.glob(USER + '/ScreenShots/**/*.png', recursive=True)) - before
        if now:
            time.sleep(0.3)
            src = sorted(now)[-1]
            shutil.move(src, f'{SHOTS}/{name}.png')
            return f'{SHOTS}/{name}.png'
    return 'no shot'


def stop():
    import psutil
    for p in psutil.process_iter(['name']):
        if (p.info['name'] or '').lower() == 'dolphin.exe': p.kill()
    try: send(['quit'])
    except OSError: pass


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'start': start(sys.argv[2])
    elif c == 'do': print(send([x.strip() for x in sys.argv[2].split(';') if x.strip()]))
    elif c == 'shot': print(shot(sys.argv[2]))
    elif c == 'stop': stop()
    elif c == 'park': park()


def grab(name):
    """PrintWindow capture of the render window (works off-screen)."""
    from PIL import Image
    gdi32 = ctypes.windll.gdi32
    hs = dolphin_windows()
    best = None
    for h in hs:
        r = wintypes.RECT(); user32.GetClientRect(h, ctypes.byref(r))
        if best is None or r.right * r.bottom > best[1]: best = (h, r.right * r.bottom, r.right, r.bottom)
    h, _, w, ht = best
    hdc = user32.GetDC(h); mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, ht); gdi32.SelectObject(mdc, bmp)
    user32.PrintWindow(h, mdc, 3)
    class BIH(ctypes.Structure):
        _fields_ = [('biSize', wintypes.DWORD), ('biWidth', wintypes.LONG), ('biHeight', wintypes.LONG), ('biPlanes', wintypes.WORD), ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD), ('biSizeImage', wintypes.DWORD), ('a', wintypes.LONG), ('b', wintypes.LONG), ('c', wintypes.DWORD), ('d', wintypes.DWORD)]
    bi = BIH(); bi.biSize = 40; bi.biWidth = w; bi.biHeight = -ht; bi.biPlanes = 1; bi.biBitCount = 32
    buf = ctypes.create_string_buffer(w * ht * 4)
    gdi32.GetDIBits(mdc, bmp, 0, ht, buf, ctypes.byref(bi), 0)
    img = Image.frombuffer('RGBA', (w, ht), buf, 'raw', 'BGRA', 0, 1).convert('RGB')
    gdi32.DeleteObject(bmp); gdi32.DeleteDC(mdc); user32.ReleaseDC(h, hdc)
    os.makedirs(SHOTS, exist_ok=True)
    img.save(f'{SHOTS}/{name}.png')
    return f'{SHOTS}/{name}.png'

if __name__ == '__main__' and sys.argv[1] == 'grab':
    print(grab(sys.argv[2]))
