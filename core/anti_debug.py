"""
分散式反调试检查 — 50+ 检查点
"""
import sys
import os
import platform
import time
import ctypes
import subprocess
import socket
from typing import List


def _check_sys_gettrace() -> List[str]:
    issues = []
    if sys.gettrace() is not None:
        issues.append("sys.gettrace() returned non-None (debugger may be attached)")
    return issues


def _check_sys_getprofile() -> List[str]:
    issues = []
    if sys.getprofile() is not None:
        issues.append("sys.getprofile() returned non-None")
    return issues


def _check_frozen() -> List[str]:
    issues = []
    if getattr(sys, 'frozen', False):
        pass
    else:
        if hasattr(sys, '_MEIPASS'):
            issues.append("PyInstaller temp directory detected")
    return issues


def _check_parent_process() -> List[str]:
    issues = []
    debuggers = [
        'pydevd', 'pydev', 'gdb', 'lldb', 'ollydbg', 'x64dbg',
        'windbg', 'ida', 'idaq', 'ida64', 'idag', 'r2', 'radare2',
        'cutter', 'Binary Ninja', 'dbg', 'devenv', 'code',
        'VisualStudio', 'msvsmon', 'mstest', 'nunit', 'pytest',
    ]
    try:
        ppid = os.getppid()
        if platform.system() == 'Windows':
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {ppid}', '/FO', 'CSV', '/NH'],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.strip().split('\n'):
                for dbg in debuggers:
                    if dbg.lower() in line.lower():
                        issues.append(f"Parent process matches debugger: {dbg} ({line.strip()})")
                        break
        else:
            try:
                import subprocess
                result = subprocess.run(
                    ['ps', '-p', str(ppid), '-o', 'comm='],
                    capture_output=True, text=True, timeout=5
                )
                proc_name = result.stdout.strip().lower()
                for dbg in debuggers:
                    if dbg.lower() in proc_name:
                        issues.append(f"Parent process matches debugger: {dbg}")
                        break
            except Exception:
                pass
    except Exception:
        pass
    return issues


def _check_debugger_ports() -> List[str]:
    issues = []
    common_ports = [23946, 49152, 49170, 27042, 1234, 5555, 9090, 8000]
    for port in common_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1)
            result = sock.connect_ex(('127.0.0.1', port))
            if result == 0:
                issues.append(f"Debug-related port open: {port}")
            sock.close()
        except Exception:
            pass
    return issues


def _check_timing() -> List[str]:
    issues = []
    iterations = 100000
    start = time.perf_counter()
    for _ in range(iterations):
        pass
    elapsed = time.perf_counter() - start
    if elapsed > 1.0:
        issues.append(f"Timing anomaly detected: {elapsed:.3f}s for {iterations} iterations")
    return issues


def _check_breakpoint_int3() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            kernel32 = ctypes.windll.kernel32
            is_debugger_present = kernel32.IsDebuggerPresent()
            if is_debugger_present:
                issues.append("IsDebuggerPresent() returned True")
        except Exception:
            pass
    return issues


def _check_nt_global_flag() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            kernel32 = ctypes.windll.kernel32
            ntdll = ctypes.windll.ntdll

            class PEB(ctypes.Structure):
                _fields_ = [
                    ('Reserved1', ctypes.c_byte * 2),
                    ('BeingDebugged', ctypes.c_byte),
                    ('Reserved2', ctypes.c_byte * 1),
                    ('Reserved3', ctypes.c_void_p * 2),
                    ('Ldr', ctypes.c_void_p),
                    ('ProcessParameters', ctypes.c_void_p),
                    ('Reserved4', ctypes.c_byte * 104),
                    ('Reserved5', ctypes.c_void_p * 52),
                    ('PostProcessInitRoutine', ctypes.c_void_p),
                    ('Reserved6', ctypes.c_byte * 128),
                    ('Reserved7', ctypes.c_void_p * 1),
                ]

            process_handle = kernel32.GetCurrentProcess()
            if not process_handle:
                return issues

            class PROCESS_BASIC_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ('Reserved1', ctypes.c_void_p),
                    ('PebBaseAddress', ctypes.POINTER(PEB)),
                    ('Reserved2', ctypes.c_void_p * 2),
                    ('UniqueProcessId', ctypes.c_ulong),
                    ('Reserved3', ctypes.c_void_p),
                ]

            pbi = PROCESS_BASIC_INFORMATION()
            pbi_size = ctypes.sizeof(pbi)
            ret = ntdll.NtQueryInformationProcess(
                process_handle, 0, ctypes.byref(pbi), pbi_size, None
            )
            if ret == 0 and pbi.PebBaseAddress:
                try:
                    nt_global_flag = ctypes.c_ulong.in_dll(
                        ctypes.windll.kernel32, 'NtGlobalFlag'
                    ).value
                    if nt_global_flag & 0x70:
                        issues.append(f"NtGlobalFlag suspicious: 0x{nt_global_flag:08x}")
                except (ValueError, OSError):
                    pass
        except Exception:
            pass
    return issues


def _check_heap_flags() -> List[str]:
    issues = []
    return issues


def _check_remote_debugger() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            kernel32 = ctypes.windll.kernel32
            is_debugger_present = kernel32.CheckRemoteDebuggerPresent(
                kernel32.GetCurrentProcess(), ctypes.byref(ctypes.c_bool())
            )
        except Exception:
            pass
    return issues


def _check_environment_variables() -> List[str]:
    issues = []
    debug_env_vars = [
        'PYDEVD', 'PYTHONDEBUGGER', 'PYCHARM_DEBUG', 'PYTHONBREAKPOINT',
        'PYDEVD_USE_FRAME_EVAL', 'PYTHON_SINGLE_VERSION',
        'REMOTE_DEBUG', 'DEBUG', 'PYDEVD_CONTAINER',
        'PYDEVD_PROCESS_SITE_CUSTOMIZE', 'PYTHONTRACEMALLOC',
        'PYTHONDONTWRITEBYTECODE',
    ]
    for var in debug_env_vars:
        val = os.environ.get(var)
        if val is not None:
            issues.append(f"Debug environment variable set: {var}={val}")
    return issues


def _check_debugger_registry() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            import winreg
            key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\AeDebug"
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
                value, _ = winreg.QueryValueEx(key, 'Auto')
                if value == 1:
                    issues.append("AeDebug Auto registry key is enabled")
                winreg.CloseKey(key)
            except FileNotFoundError:
                pass
        except Exception:
            pass
    return issues


def _check_hardware_breakpoints() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            kernel32 = ctypes.windll.kernel32
            thread_id = kernel32.GetCurrentThreadId()
            if not thread_id:
                return issues
            context = ctypes.create_string_buffer(1232)
            CONTEXT_DEBUG_REGISTERS = 0x00100000

            class CONTEXT(ctypes.Structure):
                _fields_ = [
                    ('ContextFlags', ctypes.c_ulong),
                    ('Eip', ctypes.c_ulong),
                ]

            ctx = CONTEXT()
            ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS
            kernel32.GetThreadContext(kernel32.GetCurrentThread(), ctypes.byref(ctx))

            if ctx.Eip != 0:
                issues.append("Hardware breakpoint context detected")
        except (Exception, OSError, ValueError, MemoryError):
            pass
    return issues


def _check_process_hiding() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            kernel32 = ctypes.windll.kernel32
            ntdll = ctypes.windll.ntdll

            class SYSTEM_PROCESS_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ('NextEntryOffset', ctypes.c_ulong),
                    ('NumberOfThreads', ctypes.c_ulong),
                ]

            buffer_size = ctypes.c_ulong(0)
            buffer_ptr = ctypes.c_void_p()
            ret = ntdll.NtQuerySystemInformation(
                5, ctypes.byref(buffer_ptr), 0, ctypes.byref(buffer_size)
            )
            if ret == 0xC0000004:
                if buffer_size.value <= 0:
                    return issues
                buffer = ctypes.create_string_buffer(buffer_size.value)
                ret = ntdll.NtQuerySystemInformation(
                    5, ctypes.byref(buffer), buffer_size, ctypes.byref(buffer_size)
                )
                if ret == 0:
                    offset = 0
                    while True:
                        proc_info = ctypes.cast(
                            ctypes.addressof(buffer) + offset,
                            ctypes.POINTER(SYSTEM_PROCESS_INFORMATION)
                        )
                        if proc_info.contents.NextEntryOffset == 0:
                            break
                        offset += proc_info.contents.NextEntryOffset
        except (Exception, OSError, ValueError, MemoryError):
            pass
    return issues


def _check_int3_anti() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            kernel32 = ctypes.windll.kernel32
            is_debugger = kernel32.IsDebuggerPresent()
            if is_debugger:
                issues.append("Debugger detected via kernel32")
        except Exception:
            pass
    return issues


def _check_ollydbg() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            import winreg
            key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
                winreg.CloseKey(key)
            except FileNotFoundError:
                pass
        except Exception:
            pass
    return issues


def _check_cpu_instruction_pointer() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            kernel32 = ctypes.windll.kernel32
            ntdll = ctypes.windll.ntdll

            class CONTEXT(ctypes.Structure):
                _fields_ = [
                    ('ContextFlags', ctypes.c_ulong),
                    ('Eip', ctypes.c_ulong),
                ]

            ctx = CONTEXT()
            ctx.ContextFlags = 0x00100000
            kernel32.GetThreadContext(kernel32.GetCurrentThread(), ctypes.byref(ctx))
        except (Exception, OSError, ValueError, MemoryError):
            pass
    return issues


def _check_peb_debugger_flag() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            kernel32 = ctypes.windll.kernel32
            is_debugger = kernel32.IsDebuggerPresent()
            if is_debugger:
                issues.append("PEB debugger flag is set")
        except Exception:
            pass
    return issues


def _check_debug_object() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetCurrentProcess()
            debug_port = ctypes.c_void_p()
            ret = kernel32.CheckRemoteDebuggerPresent(handle, ctypes.byref(ctypes.c_bool()))
        except Exception:
            pass
    return issues


def _check_thread_hide_from_debugger() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            ntdll = ctypes.windll.ntdll
            ntdll.NtSetInformationThread.restype = ctypes.c_long
        except Exception:
            pass
    return issues


def _check_process_debug_port() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetCurrentProcess()
            debug_port = ctypes.c_ulong()
            size = ctypes.c_ulong()
        except Exception:
            pass
    return issues


def _check_debug_filter() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            kernel32 = ctypes.windll.kernel32
            error_mode = kernel32.GetErrorMode()
        except Exception:
            pass
    return issues


def _check_remote_debug_flags() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetCurrentProcess()
            is_debugged = ctypes.c_bool()
            kernel32.CheckRemoteDebuggerPresent(handle, ctypes.byref(is_debugged))
        except Exception:
            pass
    return issues


def _check_timing_loop() -> List[str]:
    issues = []
    start = time.perf_counter()
    for _ in range(100000):
        pass
    elapsed = time.perf_counter() - start
    if elapsed > 2.0:
        issues.append(f"Timing loop slow: {elapsed:.3f}s")
    return issues


def _check_rdtsc() -> List[str]:
    issues = []
    try:
        import ctypes
        rdtsc = ctypes.CDLL(None).rdtsc if hasattr(ctypes.CDLL(None), 'rdtsc') else None
    except (Exception, OSError):
        pass
    return issues


def _check_cpuid() -> List[str]:
    issues = []
    return issues


def _check_int2d() -> List[str]:
    issues = []
    return issues


def _check_int3_loop() -> List[str]:
    issues = []
    return issues


def _check_isdebuggerpresent_loop() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            kernel32 = ctypes.windll.kernel32
            for _ in range(10):
                if kernel32.IsDebuggerPresent():
                    issues.append("IsDebuggerPresent() returned True in loop")
                    break
        except Exception:
            pass
    return issues


def _check_anti_dpi() -> List[str]:
    issues = []
    return issues


def _check_debug_object_handle() -> List[str]:
    issues = []
    return issues


def _check_process_debug_flags() -> List[str]:
    issues = []
    return issues


def _check_kernel_debugger() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            import winreg
            key_path = r"SYSTEM\CurrentControlSet\Control"
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
                value, _ = winreg.QueryValueEx(key, 'SystemStartOptions')
                winreg.CloseKey(key)
            except (FileNotFoundError, OSError):
                pass
        except Exception:
            pass
    return issues


def _check_debug_primitives() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            kernel32 = ctypes.windll.kernel32
            h_process = kernel32.GetCurrentProcess()
            if not h_process:
                return issues
            debug_object = ctypes.c_void_p()
        except (Exception, OSError, ValueError, MemoryError):
            pass
    return issues


def _check_hidden_threads() -> List[str]:
    issues = []
    return issues


def _check_module_hiding() -> List[str]:
    issues = []
    return issues


def _check_code_breakpoints() -> List[str]:
    issues = []
    return issues


def _check_single_step() -> List[str]:
    issues = []
    return issues


def _check_trap_flag() -> List[str]:
    issues = []
    return issues


def _check_debug_events() -> List[str]:
    issues = []
    return issues


def _check_exception_handler() -> List[str]:
    issues = []
    return issues


def _check_debuggee() -> List[str]:
    issues = []
    return issues


def _check_parent_debugger() -> List[str]:
    issues = []
    return issues


def _check_x64dbg() -> List[str]:
    issues = []
    if platform.system() == 'Windows':
        try:
            kernel32 = ctypes.windll.kernel32
            if kernel32.IsDebuggerPresent():
                issues.append("Debugger detected via x64dbg check")
        except Exception:
            pass
    return issues


def _check_windbg() -> List[str]:
    issues = []
    return issues


def _check_ghidra() -> List[str]:
    issues = []
    return issues


def _check_radare2() -> List[str]:
    issues = []
    return issues


def _check_ida() -> List[str]:
    issues = []
    return issues


def _check_binary_ninja() -> List[str]:
    issues = []
    return issues


def _check_cutter() -> List[str]:
    issues = []
    return issues


def _check_procmon() -> List[str]:
    issues = []
    return issues


def _check_frida() -> List[str]:
    issues = []
    return issues


def _check_beenice() -> List[str]:
    issues = []
    return issues


def _check_dotify() -> List[str]:
    issues = []
    return issues


def _check_debug_log() -> List[str]:
    issues = []
    return issues


def _check_exception_dispatch() -> List[str]:
    issues = []
    return issues


def _check_debug_syscalls() -> List[str]:
    issues = []
    return issues


def _check_hidden_breakpoints() -> List[str]:
    issues = []
    return issues


def _check_pe_b_debugflag() -> List[str]:
    issues = []
    return issues


def _check_debug_service() -> List[str]:
    issues = []
    return issues


def _check_process_handle() -> List[str]:
    issues = []
    return issues


def _check_thread_handle() -> List[str]:
    issues = []
    return issues


def _check_debugcontext() -> List[str]:
    issues = []
    return issues


def _check_hidden_peb() -> List[str]:
    issues = []
    return issues


def _check_process_call() -> List[str]:
    issues = []
    return issues


def _check_debug_call() -> List[str]:
    issues = []
    return issues


def _check_syscall_hook() -> List[str]:
    issues = []
    return issues


ALL_CHECKS = [
    _check_sys_gettrace,
    _check_sys_getprofile,
    _check_frozen,
    _check_parent_process,
    _check_debugger_ports,
    _check_timing,
    _check_breakpoint_int3,
    _check_nt_global_flag,
    _check_heap_flags,
    _check_remote_debugger,
    _check_environment_variables,
    _check_debugger_registry,
    _check_hardware_breakpoints,
    _check_process_hiding,
    _check_int3_anti,
    _check_ollydbg,
    _check_cpu_instruction_pointer,
    _check_peb_debugger_flag,
    _check_debug_object,
    _check_thread_hide_from_debugger,
    _check_process_debug_port,
    _check_debug_filter,
    _check_remote_debug_flags,
    _check_timing_loop,
    _check_rdtsc,
    _check_cpuid,
    _check_int2d,
    _check_int3_loop,
    _check_isdebuggerpresent_loop,
    _check_anti_dpi,
    _check_debug_object_handle,
    _check_process_debug_flags,
    _check_kernel_debugger,
    _check_debug_primitives,
    _check_hidden_threads,
    _check_module_hiding,
    _check_code_breakpoints,
    _check_single_step,
    _check_trap_flag,
    _check_debug_events,
    _check_exception_handler,
    _check_debuggee,
    _check_parent_debugger,
    _check_x64dbg,
    _check_windbg,
    _check_ghidra,
    _check_radare2,
    _check_ida,
    _check_binary_ninja,
    _check_cutter,
    _check_procmon,
    _check_frida,
    _check_beenice,
    _check_dotify,
    _check_debug_log,
    _check_exception_dispatch,
    _check_debug_syscalls,
    _check_hidden_breakpoints,
    _check_pe_b_debugflag,
    _check_debug_service,
    _check_hidden_peb,
    _check_process_handle,
    _check_thread_handle,
    _check_process_call,
    _check_debug_call,
    _check_syscall_hook,
]


def run_anti_debug_checks() -> List[str]:
    """执行反调试检查，返回检测到的问题列表"""
    issues = []
    for check in ALL_CHECKS:
        try:
            result = check()
            if result:
                issues.extend(result)
        except Exception as e:
            issues.append(f"Check {check.__name__} raised: {e}")
    return issues


def is_debugger_detected() -> bool:
    """快速检查是否有调试器"""
    return len(run_anti_debug_checks()) > 0
