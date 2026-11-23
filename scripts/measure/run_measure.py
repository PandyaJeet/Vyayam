"""K1 host measurement. One server, one worker, started as entrypoint.sh starts it.

Usage (from repo root, env as in DEPLOY_DECISION.md):
    python scripts/measure/run_measure.py
Prints: cold start seconds, idle RSS, peak RSS during the football walk, the
sys.modules dump (from inside the worker) after boot and after the walk.
Requires: migrate done, seed_football_test run (athlete 9100000001).
"""
import http.client, json, os, re, subprocess, sys, threading, time

PORT = 7860
HDR = {'X-Forwarded-Proto': 'https', 'Host': 'localhost'}


import ctypes
_lp = ctypes.CDLL('/usr/lib/libproc.dylib')  # macOS: `ps` is blocked in this sandbox


class _TI(ctypes.Structure):
    _fields_ = [('virt', ctypes.c_uint64), ('res', ctypes.c_uint64), ('pad', ctypes.c_uint64 * 20)]


def ps_rss(pid):
    """RSS in KB via proc_pidinfo(PROC_PIDTASKINFO); equals `ps -o rss=`."""
    ti = _TI()
    n = _lp.proc_pidinfo(pid, 4, 0, ctypes.byref(ti), ctypes.sizeof(ti))
    return ti.res // 1024 if n > 0 else 0


def children(pid):
    buf = (ctypes.c_int * 64)()
    _lp.proc_listchildpids(pid, buf, ctypes.sizeof(buf))
    return [p for p in buf if p]


class Client:
    def __init__(self):
        self.cookies = {}

    def req(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection('127.0.0.1', PORT, timeout=180)
        h = dict(HDR)
        if self.cookies:
            h['Cookie'] = '; '.join(f'{k}={v}' for k, v in self.cookies.items())
        h.update(headers or {})
        c.request(method, path, body, h)
        r = c.getresponse()
        data = r.read().decode('utf-8', 'replace')
        for k, v in r.getheaders():
            if k.lower() == 'set-cookie':
                m = re.match(r'([^=]+)=([^;]*)', v)
                self.cookies[m.group(1)] = m.group(2)
        c.close()
        return r.status, data, r.getheader('Location')


def main():
    env = dict(os.environ, DJANGO_DEBUG='False', DJANGO_ALLOWED_HOSTS='localhost,127.0.0.1',
               DJANGO_CSRF_ORIGINS='https://localhost', PYTHONPATH='scripts/measure:.')
    t0 = time.time()
    proc = subprocess.Popen(
        [sys.executable, '-m', 'gunicorn', 'measure_wsgi:application', '--bind', f'127.0.0.1:{PORT}',
         '--workers', '1', '--threads', '4', '--preload', '--timeout', '120',
         '--access-logfile', '-'], env=env, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    import atexit; atexit.register(proc.kill)  # never leave a server behind
    cl = Client()
    first = None
    while time.time() - t0 < 300:
        try:
            st, _, _ = cl.req('GET', '/healthz/')
            first = (time.time() - t0, st)
            break
        except Exception:
            time.sleep(0.1)
    print(f'COLD_START first_http_response_s={first[0]:.1f} status={first[1]}')
    # With --preload the app is imported in the master, then forked: measure both.
    kids = children(proc.pid)
    worker = kids[0]
    print(f'master_pid={proc.pid} worker_pid={worker}')
    time.sleep(30)
    print(f'IDLE_RSS_MB after 30s settle: master={ps_rss(proc.pid)/1024:.0f} worker={ps_rss(worker)/1024:.0f}')
    print('--- sys.modules after boot ---')
    print(cl.req('GET', '/__mods__')[1])

    peak = [0]; stop = [False]
    def sample():
        while not stop[0]:
            peak[0] = max(peak[0], ps_rss(worker)); time.sleep(0.2)
    th = threading.Thread(target=sample); th.start()

    hits = []
    def go(m, p, body=None, headers=None):
        t = time.time()
        st, data, loc = cl.req(m, p, body, headers)
        hits.append((m, p, st, loc, f'{time.time()-t:.2f}s', f'rss_after={ps_rss(worker)/1024:.0f}MB')); return st, data, loc
    st, page, _ = go('GET', '/login/')
    tok = cl.cookies.get('csrftoken') or re.search(r'csrfmiddlewaretoken" value="([^"]+)', page).group(1)
    form = f'phone=9100000001&password=athletepass123&csrfmiddlewaretoken={tok}'
    go('POST', '/login/', form, {'Content-Type': 'application/x-www-form-urlencoded', 'Referer': 'https://localhost/login/'})
    for p in ['/athlete/today/', '/football/sport-select/', '/football/assessment/']:
        go('GET', p)
    tests = [('hop_test', 1), ('nordic_test', 0), ('sprint_test', 0), ('pogo_test', 0),
             ('cod_test', 1), ('ybalance_test', 1), ('bench_press_test', 2), ('leg_press_test', 2)]
    for i, (tid, kind) in enumerate(tests):
        sides = ['left', 'right'] if kind == 1 else ['']
        for side in sides:
            go('GET', f'/football/assessment/{i}/' + (f'?side={side}' if side else ''))
            payload = ({'test_index': i, 'weight_kg': 60, 'reps': 8} if kind == 2 else
                       {'test_index': i, 'raw_value': '10', 'score': 3, 'side': side})
            tok = cl.cookies['csrftoken']
            go('POST', '/football/save-test-result/', json.dumps(payload),
               {'Content-Type': 'application/json', 'X-CSRFToken': tok, 'Referer': 'https://localhost/'})
    go('GET', '/football/results/')
    go('GET', '/football/matches/')
    go('GET', '/athlete/progress/')
    time.sleep(3)
    stop[0] = True; th.join()
    for h in hits:
        print(h)
    print(f'PEAK_RSS_MB worker during walk: {peak[0]/1024:.0f}')
    print(f'END_RSS_MB worker: {ps_rss(worker)/1024:.0f}')
    print('--- sys.modules after walk ---')
    print(cl.req('GET', '/__mods__')[1])
    proc.terminate()
    err = proc.stderr.read().decode()[-1500:]
    print('--- gunicorn stderr tail ---'); print(err)


main()
