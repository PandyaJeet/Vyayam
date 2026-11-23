"""Measurement-only WSGI wrapper (K1 host decision). NOT for production.

Wraps the real application and adds GET /__mods__ which reports, from inside
the serving process, the sys.modules keys matching mediapipe/cv2/tensorflow
and this process's RSS. Used by scripts/measure/run_measure.py.
"""
import os
import sys

from vyayam_project.wsgi import application as _app


import ctypes
_lp = ctypes.CDLL('/usr/lib/libproc.dylib')  # macOS: `ps` is blocked in this sandbox


class _TI(ctypes.Structure):
    _fields_ = [('virt', ctypes.c_uint64), ('res', ctypes.c_uint64), ('pad', ctypes.c_uint64 * 20)]


def rss_kb_of(pid):
    """Resident set size in KB via proc_pidinfo(PROC_PIDTASKINFO) (same number as `ps -o rss=`)."""
    ti = _TI()
    n = _lp.proc_pidinfo(pid, 4, 0, ctypes.byref(ti), ctypes.sizeof(ti))
    return ti.res // 1024 if n > 0 else 0



def _rss_kb():
    return rss_kb_of(os.getpid())


def application(environ, start_response):
    if environ.get('PATH_INFO') == '/__mods__':
        keys = sorted(k for k in sys.modules
                      if k.split('.')[0] in ('mediapipe', 'cv2', 'tensorflow'))
        top = sorted({k.split('.')[0] for k in keys})
        body = (f'pid={os.getpid()} rss_kb={_rss_kb()}\n'
                f'matching_modules={len(keys)} top_level={top}\n'
                + '\n'.join(keys[:15]) + '\n').encode()
        start_response('200 OK', [('Content-Type', 'text/plain'),
                                  ('Content-Length', str(len(body)))])
        return [body]
    return _app(environ, start_response)
