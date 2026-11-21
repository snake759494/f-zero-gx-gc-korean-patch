"""Tiny cemuhook DSU server = virtual pad for Dolphin, controlled over TCP (127.0.0.1:26761).
Commands (one per line):  press BTN [ms] | hold BTN | release BTN | stick X Y (0..255) | wait ms | quit
BTN in: A B X Y START Z L R UP DOWN LEFT RIGHT SHOT SAVE LOAD
"""
import socket, struct, threading, time, zlib, sys

SERVER_ID = 0x1234ABCD
state = {'b1': 0, 'b2': 0, 'ps': 0, 'touch': 0, 'lx': 128, 'ly': 128, 'rx': 128, 'ry': 128}
lock = threading.Lock()
clients = {}
pkt_no = 0

# DSU bit layout
# buttons1: 0x01 share 0x02 L3 0x04 R3 0x08 options 0x10 up 0x20 right 0x40 down 0x80 left
# buttons2: 0x01 L2 0x02 R2 0x04 L1 0x08 R1 0x10 triangle 0x20 circle 0x40 cross 0x80 square
MAP = {'UP': ('b1', 0x10), 'RIGHT': ('b1', 0x20), 'DOWN': ('b1', 0x40), 'LEFT': ('b1', 0x80),
       'START': ('b1', 0x08), 'SAVE': ('b1', 0x01), 'LOAD': ('b1', 0x02),
       'L': ('b2', 0x01), 'R': ('b2', 0x02), 'Z': ('b2', 0x08), 'SHOT': ('b2', 0x04),
       'Y': ('b2', 0x80), 'B': ('b2', 0x40), 'A': ('b2', 0x20), 'X': ('b2', 0x10)}


def header(payload):
    h = b'DSUS' + struct.pack('<HHII', 1001, len(payload), 0, SERVER_ID)
    pkt = h + payload
    crc = zlib.crc32(pkt) & 0xffffffff
    return pkt[:8] + struct.pack('<I', crc) + pkt[12:]


def shared(slot):
    if slot == 0:
        return struct.pack('<BBBB6sB', 0, 2, 2, 1, b'\x00\x11\x22\x33\x44\x55', 5)
    return struct.pack('<BBBB6sB', slot, 0, 0, 0, b'\0' * 6, 0)


def pad_packet():
    global pkt_no
    pkt_no += 1
    with lock:
        s = dict(state)
    an = lambda m, k: 255 if s[m] & k else 0
    p = struct.pack('<I', 0x100002) + shared(0) + struct.pack('<BI', 1, pkt_no)
    p += struct.pack('<BBBB', s['b1'], s['b2'], s['ps'], s['touch'])
    p += struct.pack('<BBBB', s['lx'], s['ly'], s['rx'], s['ry'])
    p += bytes([an('b1', 0x80), an('b1', 0x40), an('b1', 0x20), an('b1', 0x10),
                an('b2', 0x10), an('b2', 0x20), an('b2', 0x40), an('b2', 0x80),
                an('b2', 0x08), an('b2', 0x04), an('b2', 0x02), an('b2', 0x01)])
    p += b'\0' * 12
    p += struct.pack('<Q', int(time.time() * 1e6))
    p += struct.pack('<6f', 0, 0, 0, 0, 0, 0)
    return header(p)


def udp_loop():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('127.0.0.1', 26760))
    sock.settimeout(0.005)
    last = 0
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            if data[:4] == b'DSUC':
                typ = struct.unpack('<I', data[16:20])[0]
                if typ == 0x100000:
                    sock.sendto(header(struct.pack('<IH', 0x100000, 1001)), addr)
                elif typ == 0x100001:
                    n = struct.unpack('<i', data[20:24])[0]
                    for k in range(n):
                        slot = data[24 + k]
                        sock.sendto(header(struct.pack('<I', 0x100001) + shared(slot) + b'\0'), addr)
                elif typ == 0x100002:
                    clients[addr] = time.time()
        except socket.timeout:
            pass
        except ConnectionResetError:
            pass
        now = time.time()
        if now - last >= 0.004:
            last = now
            pkt = pad_packet()
            for addr, t in list(clients.items()):
                if now - t > 6:
                    del clients[addr]; continue
                try: sock.sendto(pkt, addr)
                except OSError: pass


def setbtn(name, on):
    m, k = MAP[name]
    with lock:
        state[m] = (state[m] | k) if on else (state[m] & ~k)


def handle(line):
    p = line.split()
    if not p: return 'ok'
    c = p[0].lower()
    if c == 'press':
        ms = int(p[2]) if len(p) > 2 else 120
        for n in p[1].split('+'): setbtn(n.upper(), True)
        time.sleep(ms / 1000)
        for n in p[1].split('+'): setbtn(n.upper(), False)
        time.sleep(0.08)
    elif c == 'hold':
        for n in p[1].split('+'): setbtn(n.upper(), True)
    elif c == 'release':
        for n in p[1].split('+'): setbtn(n.upper(), False)
    elif c == 'stick':
        with lock: state['lx'], state['ly'] = int(p[1]), int(p[2])
    elif c == 'wait':
        time.sleep(int(p[1]) / 1000)
    elif c == 'clients':
        return str(len(clients))
    elif c == 'quit':
        sys.exit(0)
    return 'ok'


def tcp_loop():
    srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('127.0.0.1', 26761)); srv.listen(4)
    while True:
        conn, _ = srv.accept()
        f = conn.makefile('rw')
        for line in f:
            r = handle(line.strip())
            f.write(r + '\n'); f.flush()
            if line.strip() == 'quit':
                import os; os._exit(0)
        conn.close()


if __name__ == '__main__':
    threading.Thread(target=udp_loop, daemon=True).start()
    tcp_loop()
