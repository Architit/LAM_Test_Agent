import os
import json
import time
import subprocess

def collect_active_session_telemetry():
    """Сбор телеметрии активных процессов агентов через системные команды."""
    data = {
        "timestamp": time.time(),
        "sessions": []
    }
    
    try:
        # Используем ps для сбора данных о процессах
        output = subprocess.check_output(["ps", "-eo", "pid,pcpu,rss,comm", "--no-headers"]).decode("utf-8")
        for line in output.splitlines():
            parts = line.strip().split()
            if len(parts) >= 4:
                pid, cpu, rss, comm = parts[0], parts[1], parts[2], " ".join(parts[3:])
                if any(name in comm.lower() for name in ['python', 'node', 'bash', 'lam', 'agent']):
                    data["sessions"].append({
                        "pid": pid,
                        "name": comm,
                        "cpu": cpu,
                        "mem_kb": rss,
                        "status": "MONITORED"
                    })
    except Exception as e:
        print(f"Telemetry error: {e}")
            
    with open("current_telemetry_high_freq.json", "w") as f:
        json.dump(data, f, indent=2)
    return data

if __name__ == "__main__":
    print("Collecting high-frequency telemetry via ps...")
    result = collect_active_session_telemetry()
    print(f"Collected {len(result['sessions'])} active agent-related sessions.")
