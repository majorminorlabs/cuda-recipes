from src.run_v2 import system_memory_usage_kib


def test_system_ram_uses_cgroup_v2_counter(tmp_path):
    (tmp_path / "memory.current").write_text(str(6 * 1024 * 1024))
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory/memory.usage_in_bytes").write_text(str(2 * 1024 * 1024))
    assert system_memory_usage_kib(tmp_path) == 6 * 1024


def test_system_ram_uses_cgroup_v1_counter(tmp_path):
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory/memory.usage_in_bytes").write_text(str(2 * 1024 * 1024))
    assert system_memory_usage_kib(tmp_path) == 2 * 1024


def test_system_ram_falls_back_to_proc_meminfo(tmp_path):
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemTotal: 8192 kB\nMemAvailable: 3072 kB\n")
    assert system_memory_usage_kib(tmp_path, meminfo) == 5120
