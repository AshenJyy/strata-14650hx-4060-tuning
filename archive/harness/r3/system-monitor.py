"""Read-only Windows page-in / disk / CPU counters, without launching child processes."""
import ctypes,time
from ctypes import wintypes as w
class Value(ctypes.Structure):
    _fields_=[('status',w.DWORD),('value',ctypes.c_double)]
def monitor(stop,samples,errors):
    dll=ctypes.WinDLL('pdh');query=ctypes.c_void_p()
    dll.PdhOpenQueryW.argtypes=[w.LPCWSTR,ctypes.c_size_t,ctypes.POINTER(ctypes.c_void_p)]
    dll.PdhAddEnglishCounterW.argtypes=[ctypes.c_void_p,w.LPCWSTR,ctypes.c_size_t,ctypes.POINTER(ctypes.c_void_p)]
    dll.PdhCollectQueryData.argtypes=[ctypes.c_void_p]
    dll.PdhGetFormattedCounterValue.argtypes=[ctypes.c_void_p,w.DWORD,ctypes.c_void_p,ctypes.POINTER(Value)]
    dll.PdhCloseQuery.argtypes=[ctypes.c_void_p]
    if dll.PdhOpenQueryW(None,0,ctypes.byref(query)):errors.append('open failed');return
    paths={'page_reads_s':r'\Memory\Page Reads/sec','pages_input_s':r'\Memory\Pages Input/sec',
           'disk_read_Bps':r'\PhysicalDisk(_Total)\Disk Read Bytes/sec',
           'available_MB':r'\Memory\Available MBytes','cpu_performance_pct':r'\Processor Information(_Total)\% Processor Performance'}
    handles={}
    try:
        for name,path in paths.items():
            h=ctypes.c_void_p();status=dll.PdhAddEnglishCounterW(query,path,0,ctypes.byref(h))
            if status:errors.append([name,status])
            else:handles[name]=h
        dll.PdhCollectQueryData(query)
        while not stop.wait(1):
            status=dll.PdhCollectQueryData(query)
            row={'time':time.time()}
            if status:errors.append(['collect',status]);continue
            for name,h in handles.items():
                val=Value();r=dll.PdhGetFormattedCounterValue(h,0x200,None,ctypes.byref(val))
                row[name]=val.value if r==0 and val.status in (0,1) else None
            samples.append(row)
    finally:dll.PdhCloseQuery(query)
